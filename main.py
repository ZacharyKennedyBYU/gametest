from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController

# Initialize the Ursina application
app = Ursina()

# Add a ground plane
ground = Entity(model='plane', scale=(100, 1, 100), color=color.rgb(20, 20, 100), texture='white_cube', texture_scale=(100, 100), collider='box')

# Add a first-person controller (Mymy)
player = FirstPersonController(y=2, origin_y=-.5)
player.gun = None # We can add a gun model later

# Add a sky
Sky()

# Function to handle input
def input(key):
    if key == 'escape':
        app.quit()
    if key == 'left mouse down':
        shoot()

def shoot():
    # Create a small, temporary line to represent the bullet trail
    # The origin of the bullet is slightly in front of the camera
    bullet_trail = Entity(
        parent=camera.ui, # Attach to UI so it's always visible
        model='quad',
        color=color.yellow,
        scale=(0.05, 0.2), # Adjust size as needed
        position=(0, 0, 0.1), # Start slightly in front of camera
        rotation_z=45 # Angled for a dynamic look
    )
    # Animate the trail to quickly disappear
    bullet_trail.animate_scale((0,0), duration=0.1)
    bullet_trail.animate_alpha(0, duration=0.1)
    destroy(bullet_trail, delay=0.15)

    # Animate the trail to quickly disappear
    bullet_trail.animate_scale((0,0), duration=0.1)
    bullet_trail.animate_alpha(0, duration=0.1)
    destroy(bullet_trail, delay=0.15)

    # Perform a raycast from the camera
    hit_info = raycast(camera.world_position, camera.forward, distance=100)
    if hit_info.hit:
        print(f"Hit: {hit_info.entity}")
        if isinstance(hit_info.entity, Target):
            print(f"Target at {hit_info.entity.position} shot!")
            hit_info.entity.hit() # Call a method on the target when hit

class Target(Entity): # Changed from Button to Entity for more control
    def __init__(self, position=(0,0,0), texture_name='brick'):
        super().__init__(
            parent=scene,
            model='cube',
            texture=texture_name,
            color=color.white,
            position=position,
            collider='box' # Collider is necessary for raycasting
        )

    def hit(self):
        # Action to perform when the target is hit by a raycast
        print(f"Target {self.name} at {self.position} was hit by raycast!")
        destroy(self)

# Place some targets in the scene
target1 = Target(position=(0, 2, 20), texture_name='shore') # Changed texture for variety
target2 = Target(position=(-5, 3, 25), texture_name='grass') # Changed texture for variety
target3 = Target(position=(5, 1, 15))

# Start the game
target2 = Target(position=(-5, 3, 25))
target3 = Target(position=(5, 1, 15))

# Add simple instructions
instructions = dedent('''
    <scale:1.5><black>Controls:
    WASD to move
    Mouse to look
    Left Click to shoot
    ESC to quit
''').strip()

Text(text=instructions, origin=(-.5, .5), position=(-0.65, 0.4), scale=1.2, background=True, color=color.black)


# Start the game
app.run()
