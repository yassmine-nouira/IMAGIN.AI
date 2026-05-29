import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Transform } from './transform';

describe('Transform', () => {
  let component: Transform;
  let fixture: ComponentFixture<Transform>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Transform]
    })
    .compileComponents();

    fixture = TestBed.createComponent(Transform);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
