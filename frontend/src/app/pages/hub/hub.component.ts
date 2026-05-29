import { Component } from '@angular/core';
import { Router, RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-hub',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './hub.component.html',
  styleUrls: ['./hub.component.css']
})
export class HubComponent {
  hoveredCard: string | null = null;

  constructor(private router: Router) {}

  navigateTo(path: string) {
    this.router.navigate([path]);
  }

  setHovered(card: string | null) {
    this.hoveredCard = card;
  }
}