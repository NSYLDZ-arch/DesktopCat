import sys
import os
import random
from PIL import Image
from PyQt5 import QtWidgets, QtCore, QtGui

# Scale Configuration
SCALE_FACTOR = 3

ANIMATION_CONFIG = {
    "idle": {"path": "animations/Cat-1-Idle.png", "frames": 10},
    "walk": {"path": "animations/Cat-1-Walk.png", "frames": 8},
    "run": {"path": "animations/Cat-1-Run.png", "frames": 8},
    "meow": {"path": "animations/Cat-1-Meow.png", "frames": 4},
    "sleep 1": {"path": "animations/Cat-1-Sleeping1.png", "frames": 1},
    "sleep 2": {"path": "animations/Cat-1-Sleeping2.png", "frames": 1},
    "stretch": {"path": "animations/Cat-1-Streatching.png", "frames": 13}
}

CAT_QUOTES = [
    "Meow! (Feed me right now.)", "I'm Hungry! 🐟", "Human, pay attention to me.",
    "Error 404: Cat nap required.", "Meow... I am plotting your demise.",
    "Pet me! But only exactly twice.", "Did you know I own this desktop now?",
    "Your cursor looks delicious. Can I eat it? 🖱️", "Warning: Low treat levels detected! ⚠️",
    "You've been typing a lot. Time for a break!"
]

class FoodItem(QtWidgets.QLabel):
    def __init__(self, x, y):
        super().__init__(None, QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setText("🐟")
        self.setFont(QtGui.QFont("Arial", 28))
        self.setStyleSheet("background: transparent; color: initial;")
        self.adjustSize()
        self.move(x - self.width()//2, y - self.height()//2)
        self.show()

class SpeechBubble(QtWidgets.QLabel):
    def __init__(self, text, parent=None):
        super().__init__(parent, QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.NoDropShadowWindowHint | QtCore.Qt.Tool)
        self.setText(text)
        self.setFont(QtGui.QFont("Arial", 11, QtGui.QFont.Bold))
        self.setStyleSheet("background-color: #fefedd; color: #333333; border: 2px solid black; border-radius: 5px; padding: 5px;")
        self.setAlignment(QtCore.Qt.AlignCenter)
        self.adjustSize()

class DesktopPet(QtWidgets.QLabel):
    def __init__(self):
        # Added Qt.Tool to prevent taskbar appearance
        flags = (QtCore.Qt.Window | 
                 QtCore.Qt.FramelessWindowHint | 
                 QtCore.Qt.WindowStaysOnTopHint | 
                 QtCore.Qt.NoDropShadowWindowHint | 
                 QtCore.Qt.Tool) 
        
        super().__init__(None, flags)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setWindowTitle("") # Empty title to keep it clean
        
        self.current_state = "idle"
        self.current_frame_idx = 0
        self.direction = 1  
        self.speed_x = 0
        self.speed_y = 0
        self.is_being_dragged = False
        
        self.last_drag_time = QtCore.QTime.currentTime()
        self.last_drag_pos = QtCore.QPoint(0, 0)
        self.max_drag_speed = 0.0
        self.dizzy_timer = 0
        
        self.active_food = None
        self.food_pos = None
        self.chewing_cycles = 0
        
        self.setMouseTracking(True)
        self.last_mouse_local_pos = QtCore.QPoint(0, 0)
        self.total_pet_distance = 0
        self.last_user_mouse_pos = QtGui.QCursor.pos()
        
        self.animations_right = {}
        self.animations_left = {}
        self.load_all_assets()
        
        if "idle" in self.animations_right and self.animations_right["idle"]:
            sample = self.animations_right["idle"][0]
            self.w, self.h = sample.width(), sample.height()
        else:
            self.w, self.h = 150, 150
            
        self.resize(self.w, self.h)
        
        screen = QtWidgets.QApplication.primaryScreen().geometry()
        self.screen_width = screen.width()
        self.screen_height = screen.height()
        
        self.pos_x = 400
        self.pos_y = self.screen_height - self.h - 60
        self.move(int(self.pos_x), int(self.pos_y))
        
        self.bubble = None
        
        self.physics_timer = QtCore.QTimer()
        self.physics_timer.timeout.connect(self.physics_loop)
        self.physics_timer.start(25)
        
        self.anim_timer = QtCore.QTimer()
        self.anim_timer.timeout.connect(self.animate_loop)
        self.anim_timer.start(150)
        
        self.brain_timer = QtCore.QTimer()
        self.brain_timer.timeout.connect(self.ai_brain_loop)
        self.brain_timer.start(2000) 
        
        self.show()

    def load_all_assets(self):
        for state, config in ANIMATION_CONFIG.items():
            path = config["path"]
            total_frames = config["frames"]
            if not os.path.exists(path): continue
            sheet = Image.open(path).convert("RGBA")
            sheet_w, sheet_h = sheet.size
            frame_w = sheet_w // total_frames
            
            frames_r, frames_l = [], []
            for i in range(total_frames):
                box = (i * frame_w, 0, (i + 1) * frame_w, sheet_h)
                cropped = sheet.crop(box)
                new_w, new_h = cropped.width * SCALE_FACTOR, cropped.height * SCALE_FACTOR
                scaled_r = cropped.resize((new_w, new_h), Image.Resampling.NEAREST)
                scaled_l = scaled_r.transpose(Image.FLIP_LEFT_RIGHT)
                
                qimg_r = QtGui.QImage(scaled_r.tobytes("raw", "RGBA"), scaled_r.width, scaled_r.height, QtGui.QImage.Format_RGBA8888)
                frames_r.append(QtGui.QPixmap.fromImage(qimg_r))
                qimg_l = QtGui.QImage(scaled_l.tobytes("raw", "RGBA"), scaled_l.width, scaled_l.height, QtGui.QImage.Format_RGBA8888)
                frames_l.append(QtGui.QPixmap.fromImage(qimg_l))
                    
            self.animations_right[state] = frames_r
            self.animations_left[state] = frames_l

    def physics_loop(self):
        if self.is_being_dragged or self.current_state in ["stalking_mouse", "dragging_mouse", "hunting_fish", "dizzy", "eating_fish", "meow"]:
            return

        if self.current_state in ["walk", "run"]:
            self.pos_x += self.speed_x
            self.pos_y += self.speed_y
            
            if self.pos_x < 0: self.pos_x = 0; self.direction = 1; self.speed_x *= -1
            elif self.pos_x > self.screen_width - self.w: self.pos_x = self.screen_width - self.w; self.direction = -1; self.speed_x *= -1
            
            if self.pos_y < 0: self.pos_y = 0; self.speed_y *= -1
            elif self.pos_y > self.screen_height - self.h - 60: self.pos_y = self.screen_height - self.h - 60; self.speed_y *= -1

        self.move(int(self.pos_x), int(self.pos_y))
        self.update_bubble_position()

    def animate_loop(self):
        current_mouse_pos = QtGui.QCursor.pos()

        if self.current_state == "dizzy":
            self.dizzy_timer -= 1
            if self.dizzy_timer <= 0:
                self.force_state("idle")

        elif self.current_state == "hunting_fish" and self.food_pos:
            dx = self.food_pos.x() - (self.pos_x + self.w // 2)
            dy = self.food_pos.y() - (self.pos_y + self.h // 2)
            distance = (dx**2 + dy**2)**0.5
            
            self.direction = 1 if dx >= 0 else -1
            if distance > 15:
                self.pos_x += (dx / distance) * 7.5
                self.pos_y += (dy / distance) * 7.5
                self.move(int(self.pos_x), int(self.pos_y))
            else:
                self.current_state = "eating_fish"
                self.current_frame_idx = 0
                self.chewing_cycles = 0
                if self.active_food:
                    self.active_food.close()
                    self.active_food = None

        elif self.current_state == "stalking_mouse":
            target_x = current_mouse_pos.x() - (self.w // 2)
            target_y = current_mouse_pos.y() - (self.h // 2)
            dx, dy = target_x - self.pos_x, target_y - self.pos_y
            distance = (dx**2 + dy**2)**0.5
            
            if distance > 15:
                self.direction = 1 if dx >= 0 else -1
                self.pos_x += (dx / distance) * 8.0
                self.pos_y += (dy / distance) * 8.0
                self.move(int(self.pos_x), int(self.pos_y))
                self.update_bubble_position()
            else:
                self.current_state = "dragging_mouse"
                self.current_frame_idx = 0
                self.speed_x = random.choice([-4.0, 4.0])
                self.speed_y = random.choice([-2.5, 2.5])
                self.last_user_mouse_pos = current_mouse_pos
                self.create_speech_bubble("I Caught You! 🎯")

        elif self.current_state == "dragging_mouse":
            user_moved_dist = ((current_mouse_pos.x() - self.last_user_mouse_pos.x())**2 + (current_mouse_pos.y() - self.last_user_mouse_pos.y())**2)**0.5
            if user_moved_dist > 15: 
                self.force_state("idle")
            else:
                self.pos_x += self.speed_x
                self.pos_y += self.speed_y
                self.direction = 1 if self.speed_x >= 0 else -1
                
                if self.pos_x < 0 or self.pos_x > self.screen_width - self.w: self.speed_x *= -1
                if self.pos_y < 0 or self.pos_y > self.screen_height - self.h: self.speed_y *= -1
                
                self.move(int(self.pos_x), int(self.pos_y))
                self.update_bubble_position()
                QtGui.QCursor.setPos(int(self.pos_x + (self.w // 2)), int(self.pos_y + (self.h // 2)))
                self.last_user_mouse_pos = QtGui.QCursor.pos()

        pool = self.animations_right if self.direction == 1 else self.animations_left
        render_state = self.current_state
        if self.current_state in ["hunting_fish", "stalking_mouse", "dragging_mouse"]:
            render_state = "run"
        elif self.current_state in ["eating_fish", "dizzy"]:
            render_state = "meow" 
            
        frames = pool.get(render_state, [])
        
        if frames:
            if self.current_state == "stretch" and self.current_frame_idx == len(frames) - 1:
                self.force_state("idle")
                frames = pool.get("idle", [])
            elif self.current_state == "eating_fish" and self.current_frame_idx == len(frames) - 1:
                self.chewing_cycles += 1
                if self.chewing_cycles >= 3: 
                    self.create_speech_bubble("Burp! Delicious 🐟")
                    self.force_state("idle")
                self.current_frame_idx = 0
            else:
                self.current_frame_idx = (self.current_frame_idx + 1) % len(frames)
                
            current_pixmap = frames[self.current_frame_idx]
            self.setPixmap(current_pixmap)
            self.setMask(current_pixmap.mask())
            
        self.anim_timer.setInterval(100 if render_state == "run" else 150)

    def ai_brain_loop(self):
        if self.current_state in ["hunting_fish", "eating_fish", "stalking_mouse", "dragging_mouse", "dizzy"] or self.is_being_dragged:
            return

        self.destroy_bubble()
        
        states = ["idle", "walk", "run", "meow", "sleep 1", "sleep 2", "stalking_mouse", "stretch"]
        self.current_state = random.choice(states)
        self.current_frame_idx = 0
        
        if self.current_state == "walk":
            self.direction = random.choice([1, -1])
            self.speed_x = self.direction * random.uniform(1.2, 2.5)
            self.speed_y = random.uniform(-1.0, 1.0)
        elif self.current_state == "run":
            self.direction = random.choice([1, -1])
            self.speed_x = self.direction * random.uniform(4.0, 6.0)
            self.speed_y = random.uniform(-1.5, 1.5)
        elif self.current_state == "meow":
            self.speed_x = 0; self.speed_y = 0
            self.create_speech_bubble(random.choice(CAT_QUOTES))
            if self.bubble: self.bubble.activateWindow()
        else:
            self.speed_x = 0; self.speed_y = 0
            
        self.brain_timer.setInterval(random.randint(4000, 10000))

    def drop_fish_treat(self):
        if self.active_food: self.active_food.close()
        cursor_pos = QtGui.QCursor.pos()
        self.food_pos = cursor_pos
        self.active_food = FoodItem(cursor_pos.x(), cursor_pos.y())
        self.current_state = "hunting_fish"
        self.destroy_bubble()

    def mouseMoveEvent(self, event):
        curr_local_pos = event.pos()
        delta = (curr_local_pos - self.last_mouse_local_pos)
        dist = (delta.x()**2 + delta.y()**2)**0.5
        self.last_mouse_local_pos = curr_local_pos
        
        if dist < 45:
            self.total_pet_distance += dist
            
        if self.total_pet_distance > 180: 
            self.total_pet_distance = 0
            if self.current_state not in ["hunting_fish", "eating_fish", "dragging_mouse", "dizzy"]:
                self.create_speech_bubble("Purrrrrr... ♥")
                self.force_state("idle")
                
        if event.buttons() == QtCore.Qt.LeftButton and self.is_being_dragged:
            now = QtCore.QTime.currentTime()
            elapsed = self.last_drag_time.msecsTo(now)
            if elapsed > 0:
                g_pos = event.globalPos()
                drag_delta = g_pos - self.last_drag_pos
                drag_dist = (drag_delta.x()**2 + drag_delta.y()**2)**0.5
                speed = drag_dist / elapsed
                if speed > self.max_drag_speed:
                    self.max_drag_speed = speed
                self.last_drag_pos = g_pos
                self.last_drag_time = now
                
            self.pos_x = (event.globalPos() - self.drag_position).x()
            self.pos_y = (event.globalPos() - self.drag_position).y()
            self.move(int(self.pos_x), int(self.pos_y))
            self.update_bubble_position()
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.force_state("idle")
            self.is_being_dragged = True
            self.max_drag_speed = 0.0
            self.last_drag_time = QtCore.QTime.currentTime()
            self.last_drag_pos = event.globalPos()
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == QtCore.Qt.RightButton:
            self.show_context_menu(event.pos())

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.is_being_dragged:
            self.is_being_dragged = False
            if self.max_drag_speed > 2.5: 
                self.current_state = "dizzy"
                self.dizzy_timer = 25 
                self.speed_x = 0; self.speed_y = 0
                self.create_speech_bubble("*_* Dizzy...")
            event.accept()

    def create_speech_bubble(self, text):
        self.destroy_bubble()
        self.bubble = SpeechBubble(text, self)
        self.bubble.show()
        self.update_bubble_position()

    def update_bubble_position(self):
        if self.bubble:
            bx = self.pos_x + (self.w // 2) - (self.bubble.width() // 2)
            by = self.pos_y - self.bubble.height() - 5
            self.bubble.move(int(bx), int(by))

    def destroy_bubble(self):
        if self.bubble: self.bubble.close(); self.bubble = None

    def show_context_menu(self, point):
        menu = QtWidgets.QMenu(self)
        feed_action = menu.addAction("Feed Cat 🐟")
        feed_action.triggered.connect(self.drop_fish_treat)
        menu.addSeparator()
        
        change_action = menu.addMenu("Change Action")
        for state in self.animations_right.keys():
            change_action.addAction(state.capitalize()).triggered.connect(lambda checked, s=state: self.force_state(s))
            
        stalk_action = change_action.addAction("Stalk Mouse 🎯")
        stalk_action.triggered.connect(lambda: self.force_state("stalking_mouse"))

        menu.addSeparator()
        exit_action = menu.addAction("Close Cat 🚪")
        exit_action.triggered.connect(self.close_application)
        menu.exec_(self.mapToGlobal(point))

    def force_state(self, state):
        self.destroy_bubble()
        self.current_state = state
        self.current_frame_idx = 0
        self.speed_x = 0; self.speed_y = 0
        if state == "meow":
            self.create_speech_bubble(random.choice(CAT_QUOTES))
            if self.bubble: self.bubble.activateWindow()

    def close_application(self):
        if self.active_food: self.active_food.close()
        self.destroy_bubble()
        QtWidgets.QApplication.quit()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    pet = DesktopPet()
    sys.exit(app.exec_())