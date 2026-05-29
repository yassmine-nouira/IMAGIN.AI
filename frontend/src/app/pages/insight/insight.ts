import { Component, ChangeDetectorRef, OnDestroy } from '@angular/core';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

const EMOTION_CONFIG: Record<string, {
  fr: string; color: string; bg: string;
  citation: string; author: string;
}> = {
  happy:    { fr:'Joie',      color:'#f0c040', bg:'rgba(240,192,64,0.07)',
              citation:"Le bonheur n'est pas quelque chose de tout fait. Il vient de vos propres actions.",
              author:'Dalaï-Lama' },
  sad:      { fr:'Tristesse', color:'#5a8fd0', bg:'rgba(90,143,208,0.08)',
              citation:'Les larmes sont les mots que le coeur ne peut pas dire.',
              author:'Victor Hugo' },
  angry:    { fr:'Colère',    color:'#d05050', bg:'rgba(208,80,80,0.07)',
              citation:"Quand la colère aveugle l'esprit, elle détruit la raison.",
              author:'Voltaire' },
  fear:     { fr:'Peur',      color:'#8060c0', bg:'rgba(128,96,192,0.07)',
              citation:"La peur n'est que l'anticipation de la douleur.",
              author:'Aristote' },
  surprise: { fr:'Surprise',  color:'#40c0c0', bg:'rgba(64,192,192,0.07)',
              citation:'L\'émerveillement est le début de toute connaissance.',
              author:'Socrate' },
  disgust:  { fr:'Dégoût',    color:'#60a060', bg:'rgba(96,160,96,0.07)',
              citation:'Ce qui nous révolte nous enseigne ce que nous valorisons.',
              author:'Albert Camus' },
  neutral:  { fr:'Neutre',    color:'#a0a0c0', bg:'rgba(160,160,192,0.07)',
              citation:'Le silence est la sagesse du sot et la vertu du sage.',
              author:'Bernard de Clairvaux' },
};

interface EmotionItem {
  emotion: string;
  emotion_fr: string;
  confidence: number;
  emoji: string;
}

interface AllEmotion {
  emotion: string;
  emotion_fr: string;
  probability: number;
  emoji: string;
}

interface InsightResponse {
  success: boolean;
  emotion: string;
  emotion_fr: string;
  confidence: number;
  emoji: string;
  color: string;
  description: string;
  top3: EmotionItem[];
  all_emotions: AllEmotion[];
  imageBase64: string;
  error?: string;
}

@Component({
  selector: 'app-insight',
  standalone: true,
  imports: [CommonModule, HttpClientModule, RouterModule],
  templateUrl: './insight.html',
  styleUrls: ['./insight.css']
})
export class InsightComponent implements OnDestroy {

  selectedFile: File | null = null;
  imagePreview: string | null = null;
  isLoading = false;
  errorMessage = '';
  result: InsightResponse | null = null;

  showEmojiFlash = false;
  private flashTimer: any = null;

  emotionOverlayColor = 'transparent';
  emotionConfigs = Object.entries(EMOTION_CONFIG).map(([key, cfg]) => ({
    key,
    fr: cfg.fr,
    color: cfg.color,
  }));

  quoteChars: string[] = [];
  currentQuoteAuthor = '';

  private readonly API_URL = 'http://localhost:5000';

  constructor(private http: HttpClient, private cdr: ChangeDetectorRef) {}

  ngOnDestroy() {
    if (this.flashTimer) clearTimeout(this.flashTimer);
  }

  onFileSelected(event: any): void {
    const file = event.target.files[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      this.errorMessage = 'Veuillez sélectionner une image valide.';
      return;
    }
    this.selectedFile = file;
    this.errorMessage = '';
    this.result = null;
    this.resetFeatures();
    const reader = new FileReader();
    reader.onload = (e: any) => {
      this.imagePreview = e.target.result;
      this.cdr.detectChanges();
    };
    reader.readAsDataURL(file);
  }

  analyze(): void {
    if (!this.selectedFile) { this.errorMessage = 'Aucune image sélectionnée.'; return; }
    this.isLoading = true;
    this.errorMessage = '';
    this.result = null;
    this.resetFeatures();
    const formData = new FormData();
    formData.append('image', this.selectedFile);
    this.http.post<InsightResponse>(`${this.API_URL}/insight`, formData).subscribe({
      next: (res) => {
        this.result = res;
        this.isLoading = false;
        this.applyEmotionFeatures(res);
        this.cdr.detectChanges();
      },
      error: (err) => {
        if (err.status === 0)        this.errorMessage = 'Impossible de contacter le serveur Flask.';
        else if (err.status === 503) this.errorMessage = 'Modèle Insight non disponible côté serveur.';
        else                         this.errorMessage = err.error?.error || "Erreur lors de l'analyse.";
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  private applyEmotionFeatures(res: InsightResponse): void {
    const cfg = EMOTION_CONFIG[res.emotion.toLowerCase()];
    this.showEmojiFlash = true;
    if (this.flashTimer) clearTimeout(this.flashTimer);
    this.flashTimer = setTimeout(() => {
      this.showEmojiFlash = false;
      this.cdr.detectChanges();
    }, 1500);
    this.emotionOverlayColor = cfg ? cfg.bg : 'transparent';
    if (cfg) {
      this.quoteChars = ('« ' + cfg.citation + ' »').split('');
      this.currentQuoteAuthor = cfg.author;
    }
  }

  private resetFeatures(): void {
    this.showEmojiFlash = false;
    this.emotionOverlayColor = 'transparent';
    this.quoteChars = [];
    this.currentQuoteAuthor = '';
  }

  reset(): void {
    this.selectedFile = null;
    this.imagePreview = null;
    this.result = null;
    this.errorMessage = '';
    this.resetFeatures();
  }

  getBarWidth(prob: number): number {
    if (!this.result) return 0;
    const max = Math.max(...this.result.all_emotions.map(e => e.probability));
    return max > 0 ? (prob / max) * 100 : 0;
  }
}