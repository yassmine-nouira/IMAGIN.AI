import os, io, base64
from datetime import datetime

import torch
import torch.nn as nn
import torchvision.transforms as T
import numpy as np
from PIL import Image

from flask import Flask, request, jsonify, send_from_directory, make_response
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from database import create_tables, insert_user, get_user_by_email

try:
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
    import tensorflow as tf
    TF_AVAILABLE = True
    print(f"✅ TensorFlow {tf.__version__} disponible")
except ImportError:
    TF_AVAILABLE = False
    print("⚠️  TensorFlow non installé — Style Me désactivé")

# =============================================================================
# 1. CYCLEGAN — ARTIFY
# =============================================================================

class ResidualBlock(nn.Module):
    def __init__(self, in_features):
        super().__init__()
        self.block = nn.Sequential(
            nn.ReflectionPad2d(1), nn.Conv2d(in_features, in_features, 3),
            nn.InstanceNorm2d(in_features), nn.ReLU(inplace=True),
            nn.ReflectionPad2d(1), nn.Conv2d(in_features, in_features, 3),
            nn.InstanceNorm2d(in_features),
        )
    def forward(self, x): return x + self.block(x)

class Generator(nn.Module):
    def __init__(self, input_shape=(3,256,256), num_residual_blocks=9):
        super().__init__()
        ch = input_shape[0]
        m  = [nn.ReflectionPad2d(3), nn.Conv2d(ch,64,7), nn.InstanceNorm2d(64), nn.ReLU(True)]
        inf, outf = 64, 128
        for _ in range(2):
            m += [nn.Conv2d(inf,outf,3,stride=2,padding=1), nn.InstanceNorm2d(outf), nn.ReLU(True)]
            inf, outf = outf, outf*2
        for _ in range(num_residual_blocks): m += [ResidualBlock(inf)]
        outf = inf//2
        for _ in range(2):
            m += [nn.ConvTranspose2d(inf,outf,3,stride=2,padding=1,output_padding=1), nn.InstanceNorm2d(outf), nn.ReLU(True)]
            inf, outf = outf, outf//2
        m += [nn.ReflectionPad2d(3), nn.Conv2d(64,ch,7), nn.Tanh()]
        self.model = nn.Sequential(*m)
    def forward(self, x): return self.model(x)

# =============================================================================
# 2. EFFICIENTNET — INSIGHT (émotions)
#    Architecture identifiée par inspection du checkpoint :
#    EfficientNet-B2 backbone + classifier séquentiel 7 classes (FER-2013)
#    Classes : Angry, Disgust, Fear, Happy, Neutral, Sad, Surprise
# =============================================================================

class EmotionEfficientNet(nn.Module):
    """
    EfficientNet-B2 backbone + tête de classification émotions.
    Structure du classifier déduite du checkpoint :
      Sequential(
        0: BatchNorm1d(1408),   ← sortie EfficientNet-B2 après global pool
        1: Dropout,
        2: Linear(1408 → 512),
        3: BatchNorm1d(512),
        4: ReLU,
        5: Dropout,
        6: Linear(512 → 256),
        7: BatchNorm1d(256),
        8: ReLU,
        9: Dropout,
        10: Linear(256 → 7)
      )
    """
    def __init__(self, num_classes: int = 7):
        super().__init__()
        try:
            import timm
            self.backbone = timm.create_model('efficientnet_b2', pretrained=False, num_classes=0)
            num_features  = self.backbone.num_features   # 1408 pour B2
        except ImportError:
            # Fallback : torchvision EfficientNet-B2
            from torchvision.models import efficientnet_b2
            base = efficientnet_b2(weights=None)
            # Retirer le classifier natif, garder features
            self.backbone    = nn.Sequential(*list(base.children())[:-1])
            num_features     = 1408

        self.classifier = nn.Sequential(
            nn.BatchNorm1d(num_features),          # 0
            nn.Dropout(0.3),                        # 1
            nn.Linear(num_features, 512),           # 2
            nn.BatchNorm1d(512),                    # 3
            nn.ReLU(inplace=True),                  # 4
            nn.Dropout(0.3),                        # 5
            nn.Linear(512, 256),                    # 6
            nn.BatchNorm1d(256),                    # 7
            nn.ReLU(inplace=True),                  # 8
            nn.Dropout(0.2),                        # 9
            nn.Linear(256, num_classes),            # 10
        )

    def forward(self, x):
        try:
            # timm
            feats = self.backbone(x)
        except Exception:
            # torchvision fallback
            feats = self.backbone(x).flatten(1)
        if feats.dim() > 2:
            feats = feats.mean([-2, -1])
        return self.classifier(feats)

# =============================================================================
# 3. FLASK + CORS
# =============================================================================

app = Flask(__name__)
CORS(app, origins=["http://localhost:4200"],
     allow_headers=["Content-Type","Authorization"],
     methods=["GET","POST","PUT","DELETE","OPTIONS"],
     supports_credentials=True)

@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        r = make_response()
        r.headers["Access-Control-Allow-Origin"]      = "http://localhost:4200"
        r.headers["Access-Control-Allow-Headers"]     = "Content-Type, Authorization"
        r.headers["Access-Control-Allow-Methods"]     = "GET, POST, PUT, DELETE, OPTIONS"
        r.headers["Access-Control-Allow-Credentials"] = "true"
        return r, 200

UPLOAD_FOLDER      = 'uploads'
RESULT_FOLDER      = 'results'
ARTIFY_MODEL_PATH  = "saved_models/G_AB.pth"
INSIGHT_MODEL_PATH = "saved_models/model_FINAL_CORRECT.pt"
STYLEME_MODEL_PATH = "saved_models/style_me_colab (1).keras"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER']      = UPLOAD_FOLDER
app.config['RESULT_FOLDER']      = RESULT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# =============================================================================
# 4. CHARGEMENT DES 3 MODÈLES
# =============================================================================

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# ── ARTIFY ────────────────────────────────────────────────────────────────────
artify_model = Generator().to(DEVICE)
if os.path.exists(ARTIFY_MODEL_PATH):
    artify_model.load_state_dict(torch.load(ARTIFY_MODEL_PATH, map_location=DEVICE))
    artify_model.eval()
    print(f"✅ ARTIFY   — G_AB.pth chargé sur {DEVICE}")
else:
    print(f"⚠️  ARTIFY   — {ARTIFY_MODEL_PATH} introuvable")

artify_transforms = T.Compose([
    T.Resize((256,256)), T.ToTensor(),
    T.Normalize((0.5,0.5,0.5),(0.5,0.5,0.5)),
])

# ── INSIGHT ───────────────────────────────────────────────────────────────────
insight_model = None
if os.path.exists(INSIGHT_MODEL_PATH):
    try:
        checkpoint = torch.load(INSIGHT_MODEL_PATH, map_location=DEVICE, weights_only=False)

        # Le checkpoint contient 'model_state_dict'
        state_dict = checkpoint.get('model_state_dict', checkpoint)

        # Détecter num_features depuis le checkpoint (taille BN de la couche 0)
        bn0_weight = state_dict.get('classifier.0.weight', None)
        num_features = bn0_weight.shape[0] if bn0_weight is not None else 1408

        insight_model = EmotionEfficientNet(num_classes=7).to(DEVICE)
        insight_model.load_state_dict(state_dict, strict=False)
        insight_model.eval()
        print(f"✅ INSIGHT  — model_checkpoint.pt chargé (num_features={num_features}, 7 classes)")
    except Exception as e:
        print(f"⚠️  INSIGHT  — Erreur chargement: {e}")
else:
    print(f"⚠️  INSIGHT  — {INSIGHT_MODEL_PATH} introuvable")

# ── Preprocessing INSIGHT ────────────────────────────────────────────────────
# Le checkpoint contient class_to_idx : angry→0, disgust→1, fear→2,
# happy→3, neutral→4, sad→5, surprise→6  (ordre ALPHABÉTIQUE FER-2013)
#
# On teste 4 configurations au démarrage sur une image synthétique
# et on garde celle qui produit la distribution la plus "confiante"
# (entropie minimale = prédictions les plus nettes)

def _make_insight_transform(mode: str):
    """Retourne un pipeline de preprocessing selon le mode."""
    base = [T.Resize((224, 224))]
    if mode in ('gray_imagenet', 'gray_05'):
        base.append(T.Grayscale(num_output_channels=3))
    base.append(T.ToTensor())
    if mode == 'rgb_imagenet':
        base.append(T.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225]))
    elif mode == 'gray_imagenet':
        base.append(T.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225]))
    elif mode == 'gray_05':
        base.append(T.Normalize([0.5,0.5,0.5],[0.5,0.5,0.5]))
    # 'rgb_raw' → juste /255, pas de normalize
    return T.Compose(base)

def _best_insight_transform():
    """
    Choisit le preprocessing avec l'entropie la plus basse
    (distribution la plus confiante / moins uniforme) sur une image test.
    Si le modèle n'est pas encore chargé, retourne le mode 'rgb_imagenet'.
    """
    if insight_model is None:
        return _make_insight_transform('rgb_imagenet'), 'rgb_imagenet'

    import math
    modes = ['rgb_imagenet', 'gray_imagenet', 'gray_05', 'rgb_raw']
    best_mode, best_entropy = 'rgb_imagenet', float('inf')

    # Image test : visage synthétique clair (simule une image réelle)
    test_img = Image.fromarray(
        __import__('numpy').random.randint(100, 200, (224,224,3), dtype='uint8')
    )

    for mode in modes:
        try:
            tfm    = _make_insight_transform(mode)
            tensor = tfm(test_img).unsqueeze(0).to(DEVICE)
            with torch.no_grad():
                probs = torch.softmax(insight_model(tensor), dim=1)[0].cpu()
            # Entropie de Shannon
            entropy = -sum(p * math.log(p + 1e-9) for p in probs.tolist())
            print(f"  Preprocessing '{mode}': entropie={entropy:.4f}  probs={[round(x,3) for x in probs.tolist()]}")
            if entropy < best_entropy:
                best_entropy = entropy
                best_mode    = mode
        except Exception as e:
            print(f"  Preprocessing '{mode}': erreur — {e}")

    print(f"✅ INSIGHT  — Preprocessing sélectionné : '{best_mode}' (entropie={best_entropy:.4f})")
    return _make_insight_transform(best_mode), best_mode

# Sera initialisé après le chargement du modèle (voir plus bas)
# Sélection automatique du meilleur preprocessing au chargement du module
insight_transforms, _ = _best_insight_transform()

EMOTIONS = ['Angry', 'Disgust', 'Fear', 'Happy', 'Neutral', 'Sad', 'Surprise']

EMOTION_FR = {
    'Angry'   : 'Colère',
    'Disgust' : 'Dégoût',
    'Fear'    : 'Peur',
    'Happy'   : 'Joie',
    'Neutral' : 'Neutre',
    'Sad'     : 'Tristesse',
    'Surprise': 'Surprise',
}

EMOTION_META = {
    'Angry'   : {'emoji':'😠', 'color':'#e05555', 'desc':"Une émotion intense — la frustration ou l'irritation dominent."},
    'Disgust' : {'emoji':'🤢', 'color':'#7ab648', 'desc':"Une réaction de répulsion ou de désapprobation forte."},
    'Fear'    : {'emoji':'😨', 'color':'#8a6cc9', 'desc':"Une émotion défensive face à une menace perçue."},
    'Happy'   : {'emoji':'😄', 'color':'#f5c542', 'desc':"La joie rayonne — une émotion positive et communicative."},
    'Neutral' : {'emoji':'😐', 'color':'#8899aa', 'desc':"Aucune émotion dominante — un état calme et équilibré."},
    'Sad'     : {'emoji':'😢', 'color':'#6c9ec9', 'desc':"La tristesse transparaît — une émotion de mélancolie ou de peine."},
    'Surprise': {'emoji':'😲', 'color':'#f5a342', 'desc':"Une réaction inattendue — l'étonnement ou la stupéfaction dominent."},
}

# ── STYLE ME ─────────────────────────────────────────────────────────────────
styleme_model = None
if TF_AVAILABLE and os.path.exists(STYLEME_MODEL_PATH):
    try:
        styleme_model = tf.keras.models.load_model(STYLEME_MODEL_PATH)
        print(f"✅ STYLE ME — chargé  input={styleme_model.input_shape}  output={styleme_model.output_shape}")
    except Exception as e:
        print(f"⚠️  STYLE ME — Erreur: {e}")
elif not os.path.exists(STYLEME_MODEL_PATH):
    print(f"⚠️  STYLE ME — {STYLEME_MODEL_PATH} introuvable")

CLOTHING_CATEGORIES = ["T-shirt","Chemise","Robe","Pantalon","Short","Veste","Manteau","Pull","Jupe","Combinaison"]
STYLE_MAP = {
    "T-shirt"    :{"style":"Casual",   "emoji":"👕","tips":["Jean slim","Sneakers blanches","Casquette"]},
    "Chemise"    :{"style":"Smart",    "emoji":"👔","tips":["Pantalon chino","Derby cuir","Montre sobre"]},
    "Robe"       :{"style":"Élégant",  "emoji":"👗","tips":["Escarpins","Sac à main","Bijoux discrets"]},
    "Pantalon"   :{"style":"Casual",   "emoji":"👖","tips":["T-shirt blanc","Mocassins","Ceinture cuir"]},
    "Short"      :{"style":"Sport",    "emoji":"🩳","tips":["T-shirt technique","Baskets running","Casquette sport"]},
    "Veste"      :{"style":"Smart",    "emoji":"🧥","tips":["Col roulé","Chino beige","Chelsea boots"]},
    "Manteau"    :{"style":"Chic",     "emoji":"🧣","tips":["Pull fin","Bottines","Écharpe cachemire"]},
    "Pull"       :{"style":"Casual",   "emoji":"🧶","tips":["Jean droit","Boots","Tote bag"]},
    "Jupe"       :{"style":"Élégant",  "emoji":"👗","tips":["Chemisier rentré","Sandales","Pochette"]},
    "Combinaison":{"style":"Tendance", "emoji":"✨","tips":["Sandales plates","Sac paille","Lunettes soleil"]},
}

# =============================================================================
# 5. UTILITAIRES
# =============================================================================

def allowed_file(f): return '.' in f and f.rsplit('.',1)[1].lower() in {'png','jpg','jpeg','webp'}

def pil_to_b64(img, fmt="JPEG"):
    buf = io.BytesIO()
    img.save(buf, format=fmt, quality=92)
    return base64.b64encode(buf.getvalue()).decode()

def dominant_colors(img, n=5):
    px = np.array(img.resize((100,100)).convert("RGB")).reshape(-1,3).astype(float)
    rng = np.random.default_rng(42)
    c = px[rng.choice(len(px), n, replace=False)]
    for _ in range(8):
        d  = np.linalg.norm(px[:,None]-c[None], axis=2)
        lb = np.argmin(d, axis=1)
        c  = np.array([px[lb==k].mean(axis=0) if (lb==k).any() else c[k] for k in range(n)])
    d  = np.linalg.norm(px[:,None]-c[None], axis=2)
    lb = np.argmin(d, axis=1)
    out = []
    for k in range(n):
        r,g,b = c[k].astype(int)
        out.append({"hex":f"#{r:02x}{g:02x}{b:02x}","proportion":round(float((lb==k).sum()/len(lb)),3)})
    return sorted(out, key=lambda x: -x["proportion"])

# =============================================================================
# 6. AUTH
# =============================================================================

@app.route('/api/signup', methods=['POST','OPTIONS'])
def signup():
    data = request.get_json()
    if not data: return jsonify({"success":False,"message":"Données manquantes"}), 400
    u,e,p = data.get('username','').strip(), data.get('email','').strip(), data.get('password','')
    if not u or not e or not p: return jsonify({"success":False,"message":"Tous les champs obligatoires"}), 400
    if get_user_by_email(e): return jsonify({"success":False,"message":"Email déjà utilisé"}), 409
    insert_user(u, e, generate_password_hash(p))
    return jsonify({"success":True,"message":"Compte créé avec succès"}), 201

@app.route('/api/login', methods=['POST','OPTIONS'])
def login():
    data = request.get_json()
    if not data: return jsonify({"success":False,"message":"Données manquantes"}), 400
    user = get_user_by_email(data.get('email',''))
    if user and check_password_hash(user['password'], data.get('password','')):
        return jsonify({"success":True,"user":{"username":user['username'],"email":user['email']}}), 200
    return jsonify({"success":False,"message":"Identifiants invalides"}), 401

# =============================================================================
# 7. ARTIFY — POST /transform
# =============================================================================

@app.route('/transform', methods=['POST','OPTIONS'])
def transform_image():
    if 'image' not in request.files: return jsonify({'error':'Aucune image'}), 400
    file = request.files['image']
    if not file.filename or not allowed_file(file.filename): return jsonify({'error':'Fichier invalide'}), 400
    try:
        uname = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secure_filename(file.filename)}"
        upath = os.path.join(app.config['UPLOAD_FOLDER'], uname)
        file.save(upath)
        img  = Image.open(upath).convert("RGB")
        tens = artify_transforms(img).unsqueeze(0).to(DEVICE)
        with torch.no_grad(): out = artify_model(tens)
        out = ((out.squeeze(0).cpu()*0.5)+0.5).clamp(0,1)
        pil = T.ToPILImage()(out)
        rfname = f"art_{uname}"
        pil.save(os.path.join(app.config['RESULT_FOLDER'], rfname))
        return jsonify({
            'success':True,
            'result' :f"data:image/jpeg;base64,{pil_to_b64(pil)}",
            'imageUrl':f'http://127.0.0.1:5000/results/{rfname}'
        }), 200
    except Exception as e:
        print(f"🔥 ARTIFY: {e}"); return jsonify({'error':str(e)}), 500

# =============================================================================
# 8. INSIGHT — POST /insight
# =============================================================================

@app.route('/insight', methods=['POST','OPTIONS'])
def insight():
    """
    Reçoit une image de visage, retourne :
      - emotion        : label anglais (Happy, Sad, …)
      - emotion_fr     : label français
      - confidence     : % de confiance
      - emoji          : emoji de l'émotion
      - color          : couleur associée
      - description    : texte interprétatif
      - top3           : top 3 prédictions
      - all_emotions   : tableau complet des 7 probabilités
    """
    if insight_model is None:
        return jsonify({'error': 'Modèle Insight non chargé — vérifiez saved_models/model_checkpoint.pt'}), 503

    if 'image' not in request.files:
        return jsonify({'error': 'Aucune image fournie'}), 400

    file = request.files['image']
    if not file.filename or not allowed_file(file.filename):
        return jsonify({'error': 'Fichier invalide (png, jpg, jpeg, webp)'}), 400

    try:
        uname = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secure_filename(file.filename)}"
        upath = os.path.join(app.config['UPLOAD_FOLDER'], f"insight_{uname}")
        file.save(upath)

        img_pil = Image.open(upath).convert("RGB")

        # Prétraitement
        tensor = insight_transforms(img_pil).unsqueeze(0).to(DEVICE)

        # Inférence
        with torch.no_grad():
            logits = insight_model(tensor)                    # (1, 7)
            probs  = torch.softmax(logits, dim=1)[0].cpu()   # (7,)

        pred_idx   = int(probs.argmax())
        confidence = float(probs[pred_idx]) * 100
        emotion    = EMOTIONS[pred_idx]
        meta       = EMOTION_META[emotion]

        # Top 3
        top3_idx = probs.argsort(descending=True)[:3]
        top3 = [
            {"emotion"   : EMOTIONS[i],
             "emotion_fr": EMOTION_FR[EMOTIONS[i]],
             "confidence": round(float(probs[i]) * 100, 1),
             "emoji"     : EMOTION_META[EMOTIONS[i]]['emoji']}
            for i in top3_idx
        ]

        # Toutes les émotions (pour graphique)
        all_emotions = [
            {"emotion"   : EMOTIONS[i],
             "emotion_fr": EMOTION_FR[EMOTIONS[i]],
             "probability": round(float(probs[i]) * 100, 1),
             "emoji"     : EMOTION_META[EMOTIONS[i]]['emoji']}
            for i in range(7)
        ]

        # Image encodée
        img_b64 = f"data:image/jpeg;base64,{pil_to_b64(img_pil)}"

        return jsonify({
            'success'    : True,
            'emotion'    : emotion,
            'emotion_fr' : EMOTION_FR[emotion],
            'confidence' : round(confidence, 1),
            'emoji'      : meta['emoji'],
            'color'      : meta['color'],
            'description': meta['desc'],
            'top3'       : top3,
            'all_emotions': all_emotions,
            'imageBase64': img_b64,
        }), 200

    except Exception as e:
        print(f"🔥 INSIGHT: {e}")
        return jsonify({'error': str(e)}), 500

# =============================================================================
# 9. STYLE ME — POST /styleme
# =============================================================================


@app.route('/insight/debug', methods=['POST','OPTIONS'])
def insight_debug():
    """
    Route de debug : teste les 4 preprocessing sur la même image
    et retourne les probabilités pour chacun.
    Utile pour identifier le bon preprocessing si les résultats semblent faux.
    """
    if insight_model is None:
        return jsonify({'error': 'Modèle non chargé'}), 503
    if 'image' not in request.files:
        return jsonify({'error': 'Aucune image'}), 400

    file = request.files['image']
    img_pil = Image.open(file.stream).convert("RGB")

    results = {}
    modes = ['rgb_imagenet', 'gray_imagenet', 'gray_05', 'rgb_raw']
    for mode in modes:
        try:
            tfm    = _make_insight_transform(mode)
            tensor = tfm(img_pil).unsqueeze(0).to(DEVICE)
            with torch.no_grad():
                probs = torch.softmax(insight_model(tensor), dim=1)[0].cpu()
            pred_idx = int(probs.argmax())
            results[mode] = {
                'predicted': EMOTIONS[pred_idx],
                'predicted_fr': EMOTION_FR[EMOTIONS[pred_idx]],
                'confidence': round(float(probs[pred_idx])*100, 1),
                'all': {EMOTIONS[i]: round(float(probs[i])*100,1) for i in range(7)}
            }
        except Exception as e:
            results[mode] = {'error': str(e)}

    return jsonify({'success': True, 'results': results}), 200

@app.route('/styleme', methods=['POST','OPTIONS'])
def style_me():
    if not TF_AVAILABLE: return jsonify({'error':'TensorFlow non installé'}), 503
    if styleme_model is None: return jsonify({'error':'Modèle Style Me non chargé'}), 503
    if 'image' not in request.files: return jsonify({'error':'Aucune image'}), 400
    file = request.files['image']
    if not file.filename or not allowed_file(file.filename): return jsonify({'error':'Fichier invalide'}), 400
    try:
        uname = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secure_filename(file.filename)}"
        upath = os.path.join(app.config['UPLOAD_FOLDER'], f"sm_{uname}")
        file.save(upath)
        img_pil = Image.open(upath).convert("RGB")
        ishape  = styleme_model.input_shape
        th, tw  = (ishape[1] or 224), (ishape[2] or 224)
        arr   = np.array(img_pil.resize((tw,th)), dtype=np.float32) / 255.0
        batch = np.expand_dims(arr, 0)
        preds     = styleme_model.predict(batch, verbose=0)
        pred_idx  = int(np.argmax(preds[0]))
        confidence= float(np.max(preds[0]))
        category  = CLOTHING_CATEGORIES[pred_idx] if pred_idx < len(CLOTHING_CATEGORIES) else f"Cat.{pred_idx}"
        sinfo     = STYLE_MAP.get(category, {"style":"Moderne","emoji":"👗","tips":["Accessoire tendance"]})
        top3_idx  = np.argsort(preds[0])[::-1][:3]
        top3 = [{"category": CLOTHING_CATEGORIES[i] if i < len(CLOTHING_CATEGORIES) else f"Cat.{i}",
                 "confidence": round(float(preds[0][i])*100,1)} for i in top3_idx]
        colors = dominant_colors(img_pil)
        return jsonify({
            'success':True,'category':category,'confidence':round(confidence*100,1),
            'style':sinfo['style'],'emoji':sinfo['emoji'],'tips':sinfo['tips'],
            'top3':top3,'dominant_colors':colors,
            'imageBase64':f"data:image/jpeg;base64,{pil_to_b64(img_pil)}",
        }), 200
    except Exception as e:
        print(f"🔥 STYLEME: {e}"); return jsonify({'error':str(e)}), 500

# =============================================================================
# 10. UTILITAIRES
# =============================================================================

@app.route('/results/<filename>')
def serve_result(filename): return send_from_directory(app.config['RESULT_FOLDER'], filename)

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status':'ok', 'device':DEVICE,
        'artify_loaded' : os.path.exists(ARTIFY_MODEL_PATH),
        'insight_loaded': insight_model is not None,
        'styleme_loaded': styleme_model is not None,
        'tf_available'  : TF_AVAILABLE,
    }), 200

# =============================================================================
# 11. DÉMARRAGE
# =============================================================================

if __name__ == '__main__':
    create_tables()
    print("\n🚀 SERVEUR IMAGIN.AI — http://localhost:5000")
    print(f"   ARTIFY   : {'✅' if os.path.exists(ARTIFY_MODEL_PATH) else '❌'}")
    print(f"   INSIGHT  : {'✅' if insight_model else '❌'}")
    print(f"   STYLE ME : {'✅' if styleme_model else '❌'}\n")
    app.run(debug=True, port=5000)   