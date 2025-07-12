from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import random # Ensure random is imported
from math import radians, cos, sin # Import necessary math functions

# Initialize the Ursina application
app = Ursina()

# Add a ground plane
ground = Entity(model='plane', scale=(100, 1, 100), color=color.rgb(20, 20, 100), texture='white_cube', texture_scale=(100, 100), collider='box')

# Add a first-person controller (Mymy)
player = FirstPersonController(y=2, origin_y=-.5, speed=5, jump_height=2.5, gravity=0.8) # Adjusted jump_height and gravity
player.gun = None # We can add a gun model later
player.health = 100
player.max_health = 100
player.external_velocity = Vec3(0,0,0) # For knockback
player.mass_factor = 1.0 # Higher = less knockback
player_drag_factor = 1.0 # How quickly player's external velocity decays
normal_speed = 5
sprint_speed = 8

# Weapon properties
WEAPON_HITSCAN = 'hitscan'
WEAPON_ROCKET_LAUNCHER = 'rocket_launcher'
available_weapons = [WEAPON_HITSCAN, WEAPON_ROCKET_LAUNCHER]
current_weapon_index = 0
player.current_weapon = available_weapons[current_weapon_index]

# HUD Elements
health_text = Text(text=f"Health: {player.health}", parent=camera.ui, origin=(-.5, .5), position=(-0.85, 0.45), scale=1.5, color=color.green)

# Add a sky
Sky()

# Weapon Placeholders
gun_model = Entity(parent=camera, model='cube', color=color.gray, scale=(0.1, 0.1, 0.3), position=(0.3, -0.2, 0.5), rotation=(-5, 10, -5), visible=False)
rocket_launcher_model = Entity(parent=camera, model='cylinder', color=color.dark_gray, scale=(0.15, 0.3, 0.15), position=(0.3, -0.2, 0.5), rotation=(0, 10, -5), visible=False)

# Function to update weapon model visibility
def update_weapon_model():
    if player.current_weapon == WEAPON_HITSCAN:
        gun_model.visible = True
        rocket_launcher_model.visible = False
    elif player.current_weapon == WEAPON_ROCKET_LAUNCHER:
        gun_model.visible = False
        rocket_launcher_model.visible = True
    else:
        gun_model.visible = False
        rocket_launcher_model.visible = False

# Camera bobbing parameters
bob_frequency = 10
bob_amplitude_x = 0.03
bob_amplitude_y = 0.04
bob_timer = 0
# Store the original camera pivot y offset, FPC might reset it
original_camera_pivot_y = player.camera_pivot.y

def update():
    global bob_timer
    # Camera Bobbing
    # Check if player is moving on the xz plane
    is_moving = abs(player.velocity[0]) > 0.1 or abs(player.velocity[2]) > 0.1

    if is_moving and player.grounded: # Bob only when moving and grounded
        bob_timer += time.dt * bob_frequency
        # Apply bob to the camera_pivot, which the actual camera follows
        player.camera_pivot.x = sin(bob_timer) * bob_amplitude_x
        # Add to original y, don't replace, to respect FPC's height settings
        player.camera_pivot.y = original_camera_pivot_y + cos(bob_timer / 2) * bob_amplitude_y
    else:
        bob_timer = 0
        # Smoothly reset camera_pivot offsets
        player.camera_pivot.x = lerp(player.camera_pivot.x, 0, time.dt * 10)
        player.camera_pivot.y = lerp(player.camera_pivot.y, original_camera_pivot_y, time.dt * 10)

    # Update health text color based on health percentage
    health_percentage = player.health / player.max_health if player.max_health > 0 else 0 # Avoid division by zero

    # Apply and dampen player's external velocity
    # The FirstPersonController might override direct position changes, especially Y due to gravity.
    # We'll try to influence its existing movement.
    # For XZ movement from knockback:
    if player.external_velocity.length_squared() > 0.01:
        # This is tricky because FPC calculates its own movement.
        # A simple way is to add to player's position, but FPC might clamp/override.
        # Let's try adding to controller's current direction temporarily if possible, or just add to position.
        player.x += player.external_velocity.x * time.dt
        player.z += player.external_velocity.z * time.dt
        # For Y, the FPC gravity is strong. The jump_height hack in fire_rocket is the primary way for upward.
        # If player is in air due to knockback, FPC gravity will still act.
        player.external_velocity.x *= (1 - time.dt * player_drag_factor)
        player.external_velocity.z *= (1 - time.dt * player_drag_factor)
        if abs(player.external_velocity.x) < 0.1: player.external_velocity.x = 0
        if abs(player.external_velocity.z) < 0.1: player.external_velocity.z = 0
        # Y velocity from external forces will likely be negated quickly by FPC gravity unless very high
        player.external_velocity.y *= (1 - time.dt * player_drag_factor)
        if abs(player.external_velocity.y) < 0.1: player.external_velocity.y = 0


    if health_percentage > 0.6:
        health_text.color = color.green
    elif health_percentage > 0.3:
        health_text.color = color.orange
    else:
        health_text.color = color.red
    health_text.text = f"Health: {max(0, player.health)}" # Ensure health doesn't display below 0


def player_take_damage(amount):
    if player.health <= 0: # Already game over
        return
    player.health -= amount
    print(f"Player took {amount} damage, health is now {player.health}")
    if player.health <= 0:
        game_over()

def game_over():
    print("GAME OVER")
    Text(text="GAME OVER", origin=(0,0), scale=3, color=color.red, background=True)
    player.enabled = False # Disable player movement and input
    # Potentially show a cursor and a restart button in a real game
    # For now, just quit after a delay
    invoke(application.quit, delay=5)


# Function to handle input
def input(key):
    global current_weapon_index # Declare global to modify it
    if player.health <= 0: # Disable input if game over
        if key == 'escape': # Still allow escape to quit
            application.quit()
        return

    if key == 'escape':
        app.quit()
    if key == 'left mouse down':
        shoot()
    if key == 'left shift':
        player.speed = sprint_speed
    if key == 'left shift up':
        player.speed = normal_speed
    if key == '1':
        current_weapon_index = 0
        player.current_weapon = available_weapons[current_weapon_index]
        print(f"Switched to {player.current_weapon}")
        update_weapon_model()
    if key == '2':
        current_weapon_index = 1
        player.current_weapon = available_weapons[current_weapon_index]
        print(f"Switched to {player.current_weapon}")
        update_weapon_model()
    # Optional: Mouse wheel for weapon switching
    if key == 'scroll up':
        current_weapon_index = (current_weapon_index - 1 + len(available_weapons)) % len(available_weapons)
        player.current_weapon = available_weapons[current_weapon_index]
        print(f"Switched to {player.current_weapon}")
        update_weapon_model()
    if key == 'scroll down':
        current_weapon_index = (current_weapon_index + 1) % len(available_weapons)
        player.current_weapon = available_weapons[current_weapon_index]
        print(f"Switched to {player.current_weapon}")
        update_weapon_model()

# Initialize weapon model at start
update_weapon_model()

def shoot():
    print(f"Shooting {player.current_weapon}")
    if player.current_weapon == WEAPON_HITSCAN:
        fire_hitscan()
    elif player.current_weapon == WEAPON_ROCKET_LAUNCHER:
        fire_rocket()

def fire_hitscan():
    # Create a small, temporary line to represent the bullet trail
    bullet_trail = Entity(
        parent=camera.ui, model='quad', color=color.yellow,
        scale=(0.05, 0.2), position=(0, 0, 0.1), rotation_z=45
    )
    bullet_trail.animate_scale((0,0), duration=0.1)
    bullet_trail.fade_out(duration=0.1) # Changed from animate_alpha
    destroy(bullet_trail, delay=0.15)

    hit_info = raycast(camera.world_position, camera.forward, distance=100, ignore=[player,])
    if hit_info.hit:
        print(f"Hitscan hit: {hit_info.entity}")
        if isinstance(hit_info.entity, Enemy): # Changed Target to Enemy
            print(f"Enemy at {hit_info.entity.position} shot with {player.current_weapon}!")
            hit_info.entity.hit()

def fire_rocket():
    print("Firing Rocket!")
    # Simulate rocket projectile and explosion point
    hit_info = raycast(camera.world_position, camera.forward, distance=100, ignore=[player,]) # Removed thickness argument

    explosion_point = hit_info.world_point if hit_info.hit else player.camera_pivot.world_position + camera.forward * 100

    # Create a visual effect for the explosion
    explosion_effect = Entity(model='sphere', color=color.orange, scale=0.1, position=explosion_point)
    explosion_effect.animate_scale(5, duration=0.4, curve=curve.out_expo) # Larger explosion
    explosion_effect.animate_color(color.rgba(255,100,0,0), duration=0.4, delay=0.1) # Fade out
    destroy(explosion_effect, delay=0.5)

    # Apply knockback in a radius
    blast_radius = 8
    player_knockback_force = 800 # Tuned for rocket jump
    target_knockback_force = 250 # Force for targets
    rocket_damage = 100 # Damage for targets

    # --- Player Knockback (Rocket Jump) ---
    # Calculate distance from player's feet (approx) to explosion for more accurate rocket jump feel
    player_feet_pos = player.position + Vec3(0, -player.origin_y, 0)
    dist_to_player = distance(player_feet_pos, explosion_point)

    if dist_to_player < blast_radius:
        print(f"Player in blast radius: {dist_to_player}m")
        # Direction from explosion to player's feet
        direction_to_player = (player_feet_pos - explosion_point).normalized()

        # More upward component if explosion is below the player
        if explosion_point.y < player_feet_pos.y:
            direction_to_player.y = abs(direction_to_player.y) * 1.5 + 0.5 # Emphasize upward

        knockback_strength = player_knockback_force * (1 - (dist_to_player / blast_radius))

        # Apply impulse: Modify player's y position directly for jump, and xz for movement
        # Ursina's FPC doesn't have a direct 'add_force' or velocity manipulation.
        # This is a simplified impulse.
        # player.y += direction_to_player.y * knockback_strength * time.dt * 0.3 # Scaled dt factor for jump
        # player.x += direction_to_player.x * knockback_strength * time.dt * 0.2
        # player.z += direction_to_player.z * knockback_strength * time.dt * 0.2
        knockback_impulse_player = direction_to_player * (knockback_strength / player.mass_factor) * 0.02 # Multiplied by small factor to act like impulse not continuous force
        player.external_velocity += knockback_impulse_player
        # Special handling for y to ensure rocket jump works against FPC gravity
        if knockback_impulse_player.y > 0 : player.jump_height = knockback_impulse_player.y # Temporarily set jump height for FPC

        print(f"Applied knockback impulse to player: {knockback_impulse_player}")

    # --- Target Knockback and Damage ---
    # Iterate over a copy of entities if destroying them
    for e in list(scene.entities):
        if isinstance(e, Enemy) and e.enabled: # Changed Target to Enemy
            dist_to_target = distance(e.position, explosion_point)
            if dist_to_target < blast_radius:
                print(f"Enemy {e.name} in blast radius: {dist_to_target}m")

                direction_to_target = (e.position - explosion_point).normalized()
                knockback_strength_on_enemy = target_knockback_force * (1 - (dist_to_target / blast_radius))
                knockback_impulse_enemy = direction_to_target * (knockback_strength_on_enemy / e.mass_factor) * 0.02
                e.external_velocity += knockback_impulse_enemy
                print(f"Applied knockback impulse to enemy {e.name}: {knockback_impulse_enemy}")

                e.hit(damage=rocket_damage, is_explosion=True)


class Enemy(Entity): # Renamed Target to Enemy
    def __init__(self, position=(0,0,0), texture_name='brick', health=100, speed=2, attack_damage=10, attack_cooldown=1.5, mass_factor=1.0):
        super().__init__(
            parent=scene,
            model='cube',
            texture=texture_name,
            color=color.white, # Will be tinted red when aggressive
            position=position,
            collider='box'
        )
        self.health = health
        self.max_health = health
        self.speed = speed
        self.attack_damage = attack_damage
        self.attack_cooldown_timer = 0
        self.attack_cooldown_duration = attack_cooldown
        self.is_aggressive = False # Becomes aggressive when player is close
        self.external_velocity = Vec3(0,0,0)
        self.mass_factor = mass_factor
        self.drag_factor = 1.5 # How quickly knockback velocity decays

    def update(self):
        # Apply and dampen external velocity
        self.position += self.external_velocity * time.dt
        self.external_velocity *= (1 - time.dt * self.drag_factor)
        # Stop small velocities to prevent endless sliding
        if self.external_velocity.length_squared() < 0.01:
            self.external_velocity = Vec3(0,0,0)

        if not self.enabled or player.health <= 0:
            return

        self.attack_cooldown_timer -= time.dt

        dist_to_player = distance_xz(self.position, player.position)

        # Aggro range
        if not self.is_aggressive and dist_to_player < 20:
            self.is_aggressive = True
            self.animate_color(color.rgb(255, 100, 100), duration=0.5) # Tint red

        if self.is_aggressive:
            # Look at player (optional, makes them rotate)
            self.look_at_2d(player.position, 'y') # look_at_2d ignores y difference

            # Move towards player
            move_direction = (player.position - self.position).normalized()
            self.position += move_direction * self.speed * time.dt

            # Attack if close enough and cooldown ready
            if dist_to_player < 2 and self.attack_cooldown_timer <= 0: # Attack range
                print(f"Enemy {self.name} attacks player!")
                player_take_damage(self.attack_damage)
                self.attack_cooldown_timer = self.attack_cooldown_duration
                # Simple attack animation (e.g., quick scale change)
                self.animate_scale(self.scale * 1.2, duration=0.1, curve=curve.out_sine)
                self.animate_scale(self.scale, duration=0.1, delay=0.1, curve=curve.in_sine)


    def hit(self, damage=50, is_explosion=False):
        self.health -= damage
        print(f"Enemy {self.name} hit. Health: {self.health}/{self.max_health}")

        # Become aggressive if hit
        if not self.is_aggressive:
            self.is_aggressive = True
            self.animate_color(color.rgb(255, 100, 100), duration=0.5)


        if self.health <= 0:
            if is_explosion:
                print(f"Enemy {self.name} at {self.position} was destroyed by an explosion!")
            else:
                print(f"Enemy {self.name} at {self.position} was destroyed by raycast!")
            destroy(self)
        else:
            self.blink(color.white, duration=0.15) # Blink white when hit


# Place some enemies in the scene (formerly targets)
enemy1 = Enemy(position=(0, 1, 20), texture_name='shore', health=100, speed=2.5)
enemy2 = Enemy(position=(-10, 1, 25), texture_name='grass', health=150, speed=1.5)
enemy3 = Enemy(position=(10, 1, 15), health=100, speed=2)
# Note: Enemies should spawn at y=1 (or their height/2) if ground is at y=0 for them to be on the ground.
# FirstPersonController origin is at its base, so player.y=2 means player base is on ground if ground is at 0.
# Entities origin is center by default, so y=1 for a cube of scale 1 means its base is at y=0.5. Adjusted y for enemies.

# Wave Management
current_wave_number = 0
enemies_in_scene = []
wave_hud_text = Text(text=f"Wave: {current_wave_number}", parent=camera.ui, origin=(.5, .5), position=(0.85, 0.45), scale=1.5, color=color.white)

def start_next_wave():
    global current_wave_number, enemies_in_scene
    current_wave_number += 1
    wave_hud_text.text = f"Wave: {current_wave_number}"
    print(f"Starting Wave {current_wave_number}")

    # Clear any old references if any (should be destroyed already)
    enemies_in_scene = [e for e in enemies_in_scene if e.enabled]

    num_enemies_to_spawn = current_wave_number * 2 # Example: 2 enemies for wave 1, 4 for wave 2
    for i in range(num_enemies_to_spawn):
        # Spawn enemies at random positions around the player, but not too close
        angle = random.uniform(0, 360)
        radius = random.uniform(15, 30)
        spawn_x = player.x + cos(radians(angle)) * radius
        spawn_z = player.z + sin(radians(angle)) * radius

        # Vary enemy stats slightly per wave or per enemy
        enemy_health = 100 + (current_wave_number * 10)
        enemy_speed = 2 + (current_wave_number * 0.1)

        new_enemy = Enemy(
            position=(spawn_x, 1, spawn_z),
            texture_name='brick' if i % 2 == 0 else 'grass', # Alternate textures
            health=enemy_health,
            speed=enemy_speed
        )
        enemies_in_scene.append(new_enemy)

    # Initial placeholder enemies (enemy1, enemy2, enemy3) should be removed if using wave system from start
    # For now, let's assume they are part of "wave 0" or pre-placed and the system starts after them.
    # Or, better, disable them and start wave 1 immediately.
    if 'enemy1' in globals() and enemy1.enabled: enemy1.disable()
    if 'enemy2' in globals() and enemy2.enabled: enemy2.disable()
    if 'enemy3' in globals() and enemy3.enabled: enemy3.disable()


def check_wave_completion():
    global enemies_in_scene
    # Filter out destroyed enemies
    enemies_in_scene = [e for e in enemies_in_scene if e.enabled]
    if not enemies_in_scene and player.health > 0: # All enemies defeated
        print("Wave complete!")
        start_next_wave()

# Modify update to check for wave completion
_original_update = update # Store original update
def update(): # Override update
    _original_update() # Call original camera bobbing and health text update
    if player.health > 0: # Only check wave completion if player is alive
        check_wave_completion()


# Add simple instructions
instructions = dedent('''
    <scale:1.5><black>Controls:
    WASD to move
    Mouse to look
    Left Click to shoot (1: Gun, 2: Rocket)
    Shift to Sprint
    ESC to quit
''').strip()

Text(text=instructions, origin=(-.5, .5), position=(-0.65, 0.4), scale=1.2, background=True, color=color.black)

# Start the first wave
start_next_wave()

# Start the game
app.run()
