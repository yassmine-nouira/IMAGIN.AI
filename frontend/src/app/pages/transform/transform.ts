import { Component, ChangeDetectorRef } from '@angular/core';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-transform',
  standalone: true,
  imports: [CommonModule, HttpClientModule, RouterModule],
  templateUrl: './transform.html',
  styleUrls: ['./transform.css']
})
export class TransformComponent {
  selectedFile: File | null = null;
  imagePreview: string | null = null;
  transformedImage: string | null = null;
  isLoading: boolean = false;
  errorMessage: string = '';
  successMessage: string = '';

  private readonly API_URL = 'http://localhost:5000';

  constructor(private http: HttpClient, private cdr: ChangeDetectorRef) {}

  onFileSelected(event: any): void {
    const file = event.target.files[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      this.errorMessage = 'Veuillez sélectionner une image valide (PNG, JPG, JPEG).';
      return;
    }

    if (file.size > 16 * 1024 * 1024) {
      this.errorMessage = 'L\'image ne doit pas dépasser 16 MB.';
      return;
    }

    this.selectedFile = file;
    this.errorMessage = '';
    this.successMessage = '';
    this.transformedImage = null;

    const reader = new FileReader();
    reader.onload = (e: any) => {
      this.imagePreview = e.target.result;
      this.cdr.detectChanges();
    };
    reader.readAsDataURL(file);
  }

  transform(): void {
    if (!this.selectedFile) {
      this.errorMessage = 'Aucune image sélectionnée.';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';
    this.successMessage = '';

    const formData = new FormData();
    formData.append('image', this.selectedFile);

    this.http.post<any>(`${this.API_URL}/transform`, formData).subscribe({
      next: (response) => {
        if (response.success) {
          // Priorité au base64 (affichage instantané), sinon URL
          if (response.result) {
            this.transformedImage = response.result;  // data:image/jpeg;base64,...
          } else if (response.imageUrl) {
            this.transformedImage = response.imageUrl;
          }
          this.successMessage = 'Transformation réussie !';
        } else {
          this.errorMessage = response.error || 'Erreur lors de la transformation.';
        }
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Erreur API:', err);
        if (err.status === 0) {
          this.errorMessage = 'Impossible de contacter le serveur. Vérifiez que Flask tourne sur le port 5000.';
        } else if (err.status === 500) {
          this.errorMessage = 'Erreur serveur — le modèle IA n\'est peut-être pas chargé.';
        } else {
          this.errorMessage = err.error?.error || 'Erreur de connexion avec le serveur.';
        }
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  downloadImage(): void {
    if (!this.transformedImage) return;
    const link = document.createElement('a');
    link.href = this.transformedImage;
    link.download = `artify_${Date.now()}.jpg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  reset(): void {
    this.selectedFile = null;
    this.imagePreview = null;
    this.transformedImage = null;
    this.errorMessage = '';
    this.successMessage = '';
  }
}