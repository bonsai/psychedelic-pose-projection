import oscP5.*;
import netP5.*;

OscP5 oscP5;

final int TRAIL_LENGTH = 35;
final int SKELETON_TRAIL_LENGTH = 12;

PVector[] points = new PVector[14];

ArrayList<PVector> leftTrail = new ArrayList<PVector>();
ArrayList<PVector> rightTrail = new ArrayList<PVector>();
ArrayList<PVector[]> skeletonHistory = new ArrayList<PVector[]>();
ArrayList<PVector> hipHistory = new ArrayList<PVector>();

float leftSpeed = 0;
float rightSpeed = 0;

int[][] CONNECTIONS = {
  {0, 1}, {0, 2},
  {1, 2}, {1, 3}, {3, 5},
  {2, 4}, {4, 6},
  {1, 7}, {2, 8}, {7, 8},
  {7, 9}, {9, 11},
  {8, 10}, {10, 12}
};

void setup() {
  size(1280, 720);
  colorMode(HSB, 360, 255, 255, 255);
  frameRate(60);

  oscP5 = new OscP5(this, 12000);

  for (int i = 0; i < points.length; i++) {
    points[i] = new PVector(-100, -100);
  }
}

void draw() {
  background(0, 40);

  PVector[] current = new PVector[points.length];
  for (int i = 0; i < points.length; i++) {
    current[i] = points[i].copy();
  }
  skeletonHistory.add(current);
  if (skeletonHistory.size() > SKELETON_TRAIL_LENGTH) {
    skeletonHistory.remove(0);
  }

  for (int h = 0; h < skeletonHistory.size(); h++) {
    PVector[] hist = skeletonHistory.get(h);
    float alpha = map(h, 0, skeletonHistory.size() - 1, 40, 255);
    float baseHue = (frameCount * 2 + h * 8) % 360;

    for (int[] conn : CONNECTIONS) {
      PVector a = hist[conn[0]];
      PVector b = hist[conn[1]];
      if (onScreen(a) && onScreen(b)) {
        float hue = (baseHue + conn[0] * 15) % 360;
        stroke(hue, 220, 255, alpha);
        strokeWeight(max(1, map(h, 0, skeletonHistory.size() - 1, 1, 4)));
        line(a.x, a.y, b.x, b.y);
      }
    }

    for (int i = 0; i < hist.length; i++) {
      PVector p = hist[i];
      if (onScreen(p)) {
        float hue = (baseHue + i * 18) % 360;
        fill(hue, 255, 255, alpha);
        noStroke();
        float r = map(h, 0, skeletonHistory.size() - 1, 2, 6);
        ellipse(p.x, p.y, r * 2, r * 2);
      }
    }
  }

  PVector hip = points[13];
  if (onScreen(hip)) {
    hipHistory.add(hip.copy());
    if (hipHistory.size() > 40) hipHistory.remove(0);
  }

  if (hipHistory.size() >= 5) {
    float meanX = 0;
    for (PVector p : hipHistory) meanX += p.x;
    meanX /= hipHistory.size();

    float std = 0;
    for (PVector p : hipHistory) std += sq(p.x - meanX);
    std = sqrt(std / hipHistory.size());

    if (std > 3.0) {
      float intensity = min(std / 25.0, 1.5);
      int numRings = int(2 + intensity * 3);

      noFill();
      for (int i = 0; i < numRings; i++) {
        float phase = (frameCount * 0.15 + i * 1.2) % TWO_PI;
        float radius = 30 + i * 28 + sin(phase) * 12 * intensity;
        float alpha = max(0.15, 0.7 - i * 0.12) * min(intensity, 1.0) * 255;
        float hue = (frameCount * 3 + std * 4 + i * 25) % 360;
        stroke(hue, 200, 255, alpha);
        strokeWeight(max(1, 2.5 * intensity + 1));
        ellipse(hip.x, hip.y, radius * 2, radius * 2);
      }
    }
  }

  updateTrail(leftTrail, points[5]);
  updateTrail(rightTrail, points[6]);

  drawTrail(leftTrail, speedToHue(leftSpeed));
  drawTrail(rightTrail, speedToHue(rightSpeed));

  drawWrist(points[5]);
  drawWrist(points[6]);

  fill(255);
  textSize(18);
  text("Psychedelic Pose Projection (Processing + OSC) | q: quit", 10, 25);

  if (keyPressed && key == 'q') {
    exit();
  }
}

void oscEvent(OscMessage msg) {
  if (msg.checkAddrPattern("/pose/points")) {
    if (msg.arguments().length >= 28) {
      for (int i = 0; i < 14; i++) {
        float nx = msg.get(i * 2).floatValue();
        float ny = msg.get(i * 2 + 1).floatValue();
        points[i].set(nx * width, ny * height);
      }
    }
  } else if (msg.checkAddrPattern("/left_speed")) {
    leftSpeed = msg.get(0).floatValue();
  } else if (msg.checkAddrPattern("/right_speed")) {
    rightSpeed = msg.get(0).floatValue();
  }
}

boolean onScreen(PVector p) {
  return p.x >= 0 && p.y >= 0 && p.x < width && p.y < height;
}

void updateTrail(ArrayList<PVector> trail, PVector p) {
  if (onScreen(p)) {
    trail.add(p.copy());
  }
  if (trail.size() > TRAIL_LENGTH) {
    trail.remove(0);
  }
}

void drawTrail(ArrayList<PVector> trail, float baseHue) {
  if (trail.size() < 2) return;
  noStroke();
  for (int i = 0; i < trail.size(); i++) {
    PVector p = trail.get(i);
    float alpha = map(i, 0, trail.size() - 1, 20, 220);
    float radius = map(i, 0, trail.size() - 1, 2, 9);
    float hue = (baseHue + i * 8) % 360;
    fill(hue, 255, 255, alpha);
    ellipse(p.x, p.y, radius * 2, radius * 2);
  }
}

void drawWrist(PVector p) {
  if (!onScreen(p)) return;
  noFill();
  stroke(60, 255, 255);
  strokeWeight(2);
  ellipse(p.x, p.y, 22, 22);
}

float speedToHue(float speed) {
  float maxSpeed = 45.0;
  float normalized = min(speed / maxSpeed, 1.0);
  return (normalized * 180) % 360;
}
