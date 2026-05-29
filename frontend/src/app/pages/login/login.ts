import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../services/auth';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule, CommonModule, RouterLink],
  templateUrl: './login.html', // Thabbet el esm hédha houwa bidou mte3 el HTML
  styleUrls: ['./login.css']    // Thabbet el esm hédha houwa bidou mte3 el CSS
})
export class LoginComponent {
  email: string = '';
  password: string = '';
  isLoading: boolean = false;
  errorMessage: string = '';

  constructor(
    private router: Router,
    private authService: AuthService
  ) {}

  onSubmit() {
    console.log('Tentative de connexion...'); // Bech nthabtou elli el bouton click yemchi
    this.errorMessage = '';

    if (!this.email || !this.password) {
      this.errorMessage = 'Veuillez remplir tous les champs';
      return;
    }

    this.isLoading = true;

    this.authService.login(this.email, this.password).subscribe({
      next: (response) => {
        console.log('✅ Success:', response);

        if (typeof window !== 'undefined' && window.localStorage) {
          localStorage.setItem('user', JSON.stringify(response.user));
          localStorage.setItem('isLoggedIn', 'true');
        }

        // El notification eli t7eb 3liha
        alert('✅ Sayé tconnectit! Bienvenue ' + response.user.username);

        this.isLoading = false;
        this.router.navigate(['/transform']);
      },
      error: (error) => {
        this.isLoading = false;
        console.error('❌ Erreur:', error);

        if (error.status === 401) {
          this.errorMessage = 'Email ou mot de passe incorrect';
        } else {
          this.errorMessage = 'Erreur serveur ou Backend mouch ma7loul';
        }
      }
    });
  }

  // Fonctions de secours ken el routerLink mayemchich
  goToSignup() { this.router.navigate(['/signup']); }
}
