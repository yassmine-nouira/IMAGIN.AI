import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class AuthService {

  // ✅ URL de base du backend Flask
  private readonly API_URL = 'http://localhost:5000';

  constructor(private http: HttpClient) {}

  /**
   * Inscription — appelle POST /api/signup
   * ⚠️ La route est /api/signup, PAS /api/register
   */
  register(username: string, email: string, password: string): Observable<any> {
    return this.http.post(`${this.API_URL}/api/signup`, {
      username,
      email,
      password
    });
  }

  /**
   * Connexion — appelle POST /api/login
   */
  login(email: string, password: string): Observable<any> {
    return this.http.post(`${this.API_URL}/api/login`, {
      email,
      password
    });
  }

  /**
   * Utilitaires session (localStorage)
   */
  saveSession(user: any): void {
    if (typeof window !== 'undefined' && window.localStorage) {
      localStorage.setItem('user', JSON.stringify(user));
      localStorage.setItem('isLoggedIn', 'true');
    }
  }

  getUser(): any {
    if (typeof window !== 'undefined' && window.localStorage) {
      const u = localStorage.getItem('user');
      return u ? JSON.parse(u) : null;
    }
    return null;
  }

  isLoggedIn(): boolean {
    if (typeof window !== 'undefined' && window.localStorage) {
      return localStorage.getItem('isLoggedIn') === 'true';
    }
    return false;
  }

  logout(): void {
    if (typeof window !== 'undefined' && window.localStorage) {
      localStorage.removeItem('user');
      localStorage.removeItem('isLoggedIn');
    }
  }
}