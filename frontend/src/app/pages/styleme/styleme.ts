import { Component, ChangeDetectorRef } from '@angular/core';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

interface ColorResult {
  hex: string;
  proportion: number;
}

interface Top3Item {
  category: string;
  confidence: number;
}

interface StyleMeResponse {
  success: boolean;
  category: string;
  confidence: number;
  style: string;
  emoji: string;
  tips: string[];
  top3: Top3Item[];
  dominant_colors: ColorResult[];
  imageBase64: string;
  error?: string;
}

@Component({
  selector: 'app-styleme',
  standalone: true,
  imports: [CommonModule, HttpClientModule, RouterModule],
  templateUrl: './styleme.html',
  styleUrls: ['./styleme.css']
})
export class StyleMeComponent {
  selectedFile: File | null = null;
  imagePreview: string | null = null;
  isLoading = false;
  errorMessage = '';
  result: StyleMeResponse | null = null;

  private readonly API_URL = 'http://localhost:5000';

  constructor(private http: HttpClient, private cdr: ChangeDetectorRef) {}

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

    const reader = new FileReader();
    reader.onload = (e: any) => {
      this.imagePreview = e.target.result;
      this.cdr.detectChanges();
    };
    reader.readAsDataURL(file);
  }

  analyze(): void {
    if (!this.selectedFile) {
      this.errorMessage = 'Aucune image sélectionnée.';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';
    this.result = null;

    const formData = new FormData();
    formData.append('image', this.selectedFile);

    this.http.post<StyleMeResponse>(`${this.API_URL}/styleme`, formData).subscribe({
      next: (res) => {
        this.result = res;
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Erreur StyleMe:', err);
        if (err.status === 0) {
          this.errorMessage = 'Impossible de contacter le serveur Flask (port 5000).';
        } else if (err.status === 503) {
          this.errorMessage = 'Modèle Style Me non disponible côté serveur.';
        } else {
          this.errorMessage = err.error?.error || 'Erreur lors de l\'analyse.';
        }
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  reset(): void {
    this.selectedFile = null;
    this.imagePreview = null;
    this.result = null;
    this.errorMessage = '';
  }

  // Accessibilité couleur — texte blanc ou noir selon la luminosité
  getTextColor(hex: string): string {
    const r = parseInt(hex.slice(1,3),16);
    const g = parseInt(hex.slice(3,5),16);
    const b = parseInt(hex.slice(5,7),16);
    const lum = (0.299*r + 0.587*g + 0.114*b) / 255;
    return lum > 0.5 ? '#111' : '#fff';
  }
}