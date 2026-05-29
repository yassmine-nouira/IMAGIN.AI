import { Routes } from '@angular/router';
import { HomeComponent }      from './pages/home/home.component';
import { HubComponent }       from './pages/hub/hub.component';
import { LoginComponent }     from './pages/login/login';
import { SignupComponent }    from './pages/signup/signup';
import { TransformComponent } from './pages/transform/transform';
import { InsightComponent }   from './pages/insight/insight';
import { StyleMeComponent }   from './pages/styleme/styleme';

export const routes: Routes = [
  { path: '',          component: HomeComponent  },
  { path: 'hub',       component: HubComponent   },
  { path: 'login',     component: LoginComponent },
  { path: 'signup',    component: SignupComponent },
  { path: 'transform', component: TransformComponent },  // ARTIFY
  { path: 'insight',   component: InsightComponent   },  // INSIGHT ✅
  { path: 'styleme',   component: StyleMeComponent   },  // STYLE ME ✅
  { path: '**',        redirectTo: '' }
];