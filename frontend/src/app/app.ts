import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
 templateUrl: './app.component.html',     // ← CHANGE ICI
  styleUrl: './app.css'
})
export class AppComponent {
  title = 'artify-frontend';
}
