import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-signup',
  standalone: true,
  imports: [FormsModule, CommonModule],
  templateUrl: './signup.html',
  styleUrls: ['./signup.css']
})
export class SignupComponent {
  username: string = '';
  email: string = '';
  password: string = '';
  confirmPassword: string = '';
  isLoading: boolean = false;
  errorMessage: string = '';
  successMessage: string = '';

  constructor(
    private router: Router,
    private authService: AuthService
  ) {}

  onSubmit() {
    this.isLoading = true;
    this.errorMessage = '';
    this.successMessage = '';

    if (this.password !== this.confirmPassword) {
      this.errorMessage = 'Les mots de passe ne correspondent pas';
      this.isLoading = false;
      return;
    }

    this.authService.register(this.username, this.email, this.password).subscribe({
      next: (response) => {
        console.log('Reponse:', response);
        if (response.success) {
          this.successMessage = 'Compte cree avec succes ! Redirection...';
          setTimeout(() => {
            this.router.navigate(['/login']);
          }, 2000);
        }
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Erreur:', error);
        this.errorMessage = error.error?.message || 'Erreur lors de la creation du compte';
        this.isLoading = false;
      }
    });
  }

  goToLogin() {
    this.router.navigate(['/login']);
  }
}
