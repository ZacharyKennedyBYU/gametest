from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController

# Initialize the Ursina application
app = Ursina()

# Add a ground plane
ground = Entity(model='plane', scale=(100, 1, 100), color=color.rgb(20, 20, 100), texture='white_cube', texture_scale=(100, 100), collider='box')

# Add a first-person controller (Mymy)
player = FirstPersonController(y=2, origin_y=-.5, speed=5) # Default speed
player.gun = None # We can add a gun model later
normal_speed = 5
sprint_speed = 8

# Weapon properties
WEAPON_HITSCAN = 'hitscan'
WEAPON_ROCKET_LAUNCHER = 'rocket_launcher'
available_weapons = [WEAPON_HITSCAN, WEAPON_ROCKET_LAUNCHER]
current_weapon_index = 0
player.current_weapon = available_weapons[current_weapon_index]

# Add a sky
Sky()

# Function to handle input
def input(key):
    global current_weapon_index # Declare global to modify it
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
    if key == '2':
        current_weapon_index = 1
        player.current_weapon = available_weapons[current_weapon_index]
        print(f"Switched to {player.current_weapon}")
    # Optional: Mouse wheel for weapon switching
    if key == 'scroll up':
        current_weapon_index = (current_weapon_index - 1 + len(available_weapons)) % len(available_weapons)
        player.current_weapon = available_weapons[current_weapon_index]
        print(f"Switched to {player.current_weapon}")
    if key == 'scroll down':
        current_weapon_index = (current_weapon_index + 1) % len(available_weapons)
        player.current_weapon = available_weapons[current_weapon_index]
        print(f"Switched to {player.current_weapon}")


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
    bullet_trail.animate_alpha(0, duration=0.1)
    destroy(bullet_trail, delay=0.15)

    hit_info = raycast(camera.world_position, camera.forward, distance=100, ignore=[player,])
    if hit_info.hit:
        print(f"Hitscan hit: {hit_info.entity}")
        if isinstance(hit_info.entity, Target):
            print(f"Target at {hit_info.entity.position} shot with {player.current_weapon}!")
            hit_info.entity.hit()

def fire_rocket():
    print("Firing Rocket!")
    # Simulate rocket projectile and explosion point
    hit_info = raycast(camera.world_position, camera.forward, distance=100, ignore=[player,], thickness=0.5) # Added thickness for rocket

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
        player.y += direction_to_player.y * knockback_strength * time.dt * 0.3 # Scaled dt factor for jump
        player.x += direction_to_player.x * knockback_strength * time.dt * 0.2
        player.z += direction_to_player.z * knockback_strength * time.dt * 0.2

        print(f"Applied knockback to player. Impulse: {direction_to_player * knockback_strength * time.dt}")

    # --- Target Knockback and Damage ---
    # Iterate over a copy of entities if destroying them
    for e in list(scene.entities):
        if isinstance(e, Target) and e.enabled: # Check if target is active
            dist_to_target = distance(e.position, explosion_point)
            if dist_to_target < blast_radius:
                print(f"Target {e.name} in blast radius: {dist_to_target}m")

                # Apply knockback (simple position change for now, can be improved with physics)
                # direction_to_target = (e.position - explosion_point).normalized()
                # knockback_strength_target = target_knockback_force * (1 - (dist_to_target / blast_radius))
                # e.position += direction_to_target * knockback_strength_target * time.dt # This needs careful tuning

                # For now, just damage/destroy the target
                e.hit(damage=rocket_damage, is_explosion=True)


class Target(Entity):
    def __init__(self, position=(0,0,0), texture_name='brick', health=100):
        super().__init__(
            parent=scene,
            model='cube',
            texture=texture_name,
            color=color.white,
            position=position,
            collider='box' # Collider is necessary for raycasting
        )
        self.health = health
        self.max_health = health

    def hit(self, damage=50, is_explosion=False): # Default damage for hitscan
        self.health -= damage
        print(f"Target {self.name} hit. Health: {self.health}/{self.max_health}")

        if self.health <= 0:
            if is_explosion:
                print(f"Target {self.name} at {self.position} was destroyed by an explosion!")
            else:
                print(f"Target {self.name} at {self.position} was destroyed by raycast!")
            destroy(self)
        else:
            # Visual feedback for getting hit but not destroyed
            self.blink(color.red, duration=0.1)


# Place some targets in the scene
target1 = Target(position=(0, 2, 20), texture_name='shore', health=100)
target2 = Target(position=(-5, 3, 25), texture_name='grass', health=150)
target3 = Target(position=(5, 1, 15), health=100)

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

# Start the game
app.run()
