// ==========================================
// PROJECT NIGHTWATCH V2.0
// Arduino Uno + HC-SR04 + LED
// ==========================================

const int trigPin = 5;
const int echoPin = 6;
const int ledPin = 10;

const int warningDistance = 18;

float getDistance() {

    digitalWrite(trigPin, LOW);
    delayMicroseconds(2);

    digitalWrite(trigPin, HIGH);
    delayMicroseconds(10);

    digitalWrite(trigPin, LOW);

    long duration = pulseIn(echoPin, HIGH, 30000);

    if (duration == 0) {
        return -1;
    }

    return duration * 0.0343 / 2;
}

void setup() {

    pinMode(trigPin, OUTPUT);
    pinMode(echoPin, INPUT);
    pinMode(ledPin, OUTPUT);

    Serial.begin(9600);

    digitalWrite(ledPin, LOW);

    Serial.println("PROJECT NIGHTWATCH V2.0");
    Serial.println("System initialized");
}

void loop() {

    float distance = getDistance();

    if (distance < 0) {

        Serial.println("No echo");

        delay(300);
        return;
    }

    Serial.print("Distance: ");
    Serial.print(distance, 2);
    Serial.println(" cm");

    if (distance <= warningDistance) {

        digitalWrite(ledPin, HIGH);

        Serial.println("ALERT: OBJECT DETECTED!");

    } else {

        digitalWrite(ledPin, LOW);

        Serial.println("STATUS: NORMAL");
    }

    delay(300);
}
