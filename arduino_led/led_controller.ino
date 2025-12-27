/*
 * Arduino LED Controller для RobotEva
 * Управление 7-цветным мигающим LED модулем
 * 
 * Команды через Serial:
 * SET_STATUS:status - установка статуса (ready, listening, thinking, speaking, active, sleep, error)
 * SET_COLOR:color - установка цвета (red, green, blue, yellow, cyan, magenta, white, off)
 */

// Определение пинов для RGB LED (или используйте готовый модуль)
// Если используется готовый модуль, настройте пины соответственно
const int RED_PIN = 9;
const int GREEN_PIN = 10;
const int BLUE_PIN = 11;

// Статусы и цвета
String currentStatus = "ready";
String currentColor = "blue";

void setup() {
  Serial.begin(9600);
  
  // Настройка пинов LED
  pinMode(RED_PIN, OUTPUT);
  pinMode(GREEN_PIN, OUTPUT);
  pinMode(BLUE_PIN, OUTPUT);
  
  // Начальное состояние
  setColor("blue");
  
  Serial.println("LED Controller готов");
}

void loop() {
  // Обработка команд из Serial
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    if (command.startsWith("SET_STATUS:")) {
      String status = command.substring(11);
      setStatus(status);
    }
    else if (command.startsWith("SET_COLOR:")) {
      String color = command.substring(10);
      setColor(color);
    }
  }
  
  // Мигание для активных статусов
  if (currentStatus == "listening" || currentStatus == "active") {
    blinkColor(currentColor, 500);
  }
  else if (currentStatus == "thinking") {
    blinkColor(currentColor, 300);
  }
  else if (currentStatus == "sleep") {
    blinkColor("red", 2000);
  }
  
  delay(10);
}

void setStatus(String status) {
  currentStatus = status;
  
  // Маппинг статусов на цвета
  if (status == "ready") {
    setColor("blue");
  }
  else if (status == "listening") {
    setColor("green");
  }
  else if (status == "thinking") {
    setColor("yellow");
  }
  else if (status == "speaking") {
    setColor("cyan");
  }
  else if (status == "active") {
    setColor("magenta");
  }
  else if (status == "sleep") {
    setColor("red");
  }
  else if (status == "error") {
    setColor("red");
  }
}

void setColor(String color) {
  currentColor = color;
  
  // Установка RGB значений
  if (color == "red") {
    analogWrite(RED_PIN, 255);
    analogWrite(GREEN_PIN, 0);
    analogWrite(BLUE_PIN, 0);
  }
  else if (color == "green") {
    analogWrite(RED_PIN, 0);
    analogWrite(GREEN_PIN, 255);
    analogWrite(BLUE_PIN, 0);
  }
  else if (color == "blue") {
    analogWrite(RED_PIN, 0);
    analogWrite(GREEN_PIN, 0);
    analogWrite(BLUE_PIN, 255);
  }
  else if (color == "yellow") {
    analogWrite(RED_PIN, 255);
    analogWrite(GREEN_PIN, 255);
    analogWrite(BLUE_PIN, 0);
  }
  else if (color == "cyan") {
    analogWrite(RED_PIN, 0);
    analogWrite(GREEN_PIN, 255);
    analogWrite(BLUE_PIN, 255);
  }
  else if (color == "magenta") {
    analogWrite(RED_PIN, 255);
    analogWrite(GREEN_PIN, 0);
    analogWrite(BLUE_PIN, 255);
  }
  else if (color == "white") {
    analogWrite(RED_PIN, 255);
    analogWrite(GREEN_PIN, 255);
    analogWrite(BLUE_PIN, 255);
  }
  else if (color == "off") {
    analogWrite(RED_PIN, 0);
    analogWrite(GREEN_PIN, 0);
    analogWrite(BLUE_PIN, 0);
  }
}

void blinkColor(String color, int interval) {
  static unsigned long lastBlink = 0;
  static bool isOn = true;
  
  unsigned long currentTime = millis();
  
  if (currentTime - lastBlink >= interval) {
    if (isOn) {
      setColor(color);
    } else {
      setColor("off");
    }
    isOn = !isOn;
    lastBlink = currentTime;
  }
}

