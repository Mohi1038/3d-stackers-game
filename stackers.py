import glfw
from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram, compileShader
import numpy as np
import pyrr
import math
import time
import ctypes



if not glfw.init():
    raise Exception("GLFW not initialized")


# Set up OpenGL context for macOS
glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 1)
glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, GL_TRUE)

WINDOW_TITLE = "3D Stacker Game"
window = glfw.create_window(800, 600, WINDOW_TITLE, None, None)
glfw.make_context_current(window)

glEnable(GL_DEPTH_TEST)



VAO = glGenVertexArrays(1)
glBindVertexArray(VAO)



def load_shader(vertex_path, fragment_path):
    with open(vertex_path, "r") as f:
        vertex_src = f.read()
    with open(fragment_path, "r") as f:
        fragment_src = f.read()

    shader = compileProgram(
        compileShader(vertex_src, GL_VERTEX_SHADER),
        compileShader(fragment_src, GL_FRAGMENT_SHADER)
    )
    return shader

shader = load_shader("shaders/basic.vert", "shaders/basic.frag")
glUseProgram(shader)



vertices = np.array([
    -0.5,-0.5, 0.5,
     0.5,-0.5, 0.5,
     0.5, 0.5, 0.5,
    -0.5, 0.5, 0.5,

    -0.5,-0.5,-0.5,
     0.5,-0.5,-0.5,
     0.5, 0.5,-0.5,
    -0.5, 0.5,-0.5,
], dtype=np.float32)

indices = np.array([
    0,1,2, 2,3,0,
    4,5,6, 6,7,4,
    0,4,7, 7,3,0,
    1,5,6, 6,2,1,
    3,2,6, 6,7,3,
    0,1,5, 5,4,0
], dtype=np.uint32)

VBO = glGenBuffers(1)
EBO = glGenBuffers(1)

glBindBuffer(GL_ARRAY_BUFFER, VBO)
glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, EBO)
glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * 4, ctypes.c_void_p(0))
glEnableVertexAttribArray(0)



model_loc = glGetUniformLocation(shader, "model")
view_loc = glGetUniformLocation(shader, "view")
proj_loc = glGetUniformLocation(shader, "projection")
color_loc = glGetUniformLocation(shader, "cubeColor")



projection = pyrr.matrix44.create_perspective_projection(
    45, 800/600, 0.1, 100
)



cube_positions = []
current_layer = 0
cube_width = 1.0

speed = 2.0
move_range = 3.0
start_time = time.time()

space_pressed = False
game_over = False
fall_y = 0


def draw_hud_score(score):
    # Draws the score in the top-left using a simple block font
    score = max(0, score)
    ortho_projection = pyrr.matrix44.create_orthogonal_projection(
        0, 800, 0, 600, -1, 1
    )
    ortho_view = pyrr.matrix44.create_identity(dtype=np.float32)
    glUniformMatrix4fv(view_loc, 1, GL_FALSE, ortho_view)
    glUniformMatrix4fv(proj_loc, 1, GL_FALSE, ortho_projection)
    score_str = str(score)
    glyphs = {
        "0": ["111","101","101","101","111"],
        "1": ["010","110","010","010","111"],
        "2": ["111","001","111","100","111"],
        "3": ["111","001","111","001","111"],
        "4": ["101","101","111","001","001"],
        "5": ["111","100","111","001","111"],
        "6": ["111","100","111","101","111"],
        "7": ["111","001","010","010","010"],
        "8": ["111","101","111","101","111"],
        "9": ["111","101","111","001","111"],
    }
    cell_w = 6.0
    cell_h = 8.0
    digit_cols = 3
    digit_rows = 5
    digit_w = digit_cols * cell_w
    digit_h = digit_rows * cell_h
    digit_spacing = digit_w + 4.0
    start_x = 20.0
    start_y = 572.0
    glUniform3f(color_loc, 0.95, 0.95, 0.98)
    for di, ch in enumerate(score_str):
        pattern = glyphs.get(ch, glyphs["0"])
        base_x = start_x + di * digit_spacing
        base_y = start_y
        for row in range(digit_rows):
            for col in range(digit_cols):
                if pattern[row][col] == "1":
                    cx = base_x + col * cell_w
                    cy = base_y - row * cell_h
                    scale = pyrr.matrix44.create_from_scale(
                        pyrr.Vector3([cell_w * 0.5, cell_h * 0.5, 1])
                    )
                    translate = pyrr.matrix44.create_from_translation(
                        pyrr.Vector3([cx, cy, 0])
                    )
                    model_digit = pyrr.matrix44.multiply(scale, translate)
                    glUniformMatrix4fv(model_loc, 1, GL_FALSE, model_digit)
                    glDrawElements(GL_TRIANGLES, len(indices), GL_UNSIGNED_INT, None)



while not glfw.window_should_close(window):

    glfw.poll_events()
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)


    # Camera follows the stack
    camera_height = 8 + current_layer * 0.8
    camera_pos = pyrr.Vector3([6, camera_height, 12])
    target = pyrr.Vector3([0, current_layer, 0])
    view = pyrr.matrix44.create_look_at(
        camera_pos,
        target,
        pyrr.Vector3([0,1,0])
    )

    glUniformMatrix4fv(view_loc, 1, GL_FALSE, view)
    glUniformMatrix4fv(proj_loc, 1, GL_FALSE, projection)

    current_time = time.time() - start_time
    active_x = math.sin(current_time * speed) * move_range


    # Draw all stacked cubes

    for pos in cube_positions:
        model = pyrr.matrix44.create_from_translation(
            pyrr.Vector3([pos[0], pos[1], 0])
        )
        glUniformMatrix4fv(model_loc, 1, GL_FALSE, model)
        glUniform3f(color_loc, 0.2, 0.6, 0.9)
        glDrawElements(GL_TRIANGLES, len(indices), GL_UNSIGNED_INT, None)


    # Draw the moving active cube

    if not game_over:
        model = pyrr.matrix44.create_from_translation(
            pyrr.Vector3([active_x, current_layer, 0])
        )

        if cube_positions:
            previous_x = cube_positions[-1][0]
            if abs(active_x - previous_x) < cube_width * 0.5:
                glUniform3f(color_loc, 0.2, 0.8, 0.2)
            else:
                glUniform3f(color_loc, 0.8, 0.2, 0.2)
        else:
            glUniform3f(color_loc, 0.9, 0.9, 0.2)

        glUniformMatrix4fv(model_loc, 1, GL_FALSE, model)
        glDrawElements(GL_TRIANGLES, len(indices), GL_UNSIGNED_INT, None)


    # Handle dropping the cube

    if glfw.get_key(window, glfw.KEY_SPACE) == glfw.PRESS and not space_pressed:
        space_pressed = True

        if cube_positions:
            previous_x = cube_positions[-1][0]
            if abs(active_x - previous_x) > cube_width:
                game_over = True
            else:
                cube_positions.append((active_x, current_layer))
                current_layer += 1
        else:
            cube_positions.append((active_x, current_layer))
            current_layer += 1

    if glfw.get_key(window, glfw.KEY_SPACE) == glfw.RELEASE:
        space_pressed = False


    # Animate the falling cube on game over

    if game_over:
        fall_y -= 0.1
        model = pyrr.matrix44.create_from_translation(
            pyrr.Vector3([active_x, current_layer + fall_y, 0])
        )
        glUniformMatrix4fv(model_loc, 1, GL_FALSE, model)
        glUniform3f(color_loc, 1.0, 0.0, 0.0)
        glDrawElements(GL_TRIANGLES, len(indices), GL_UNSIGNED_INT, None)

        if fall_y < -5:
            cube_positions.clear()
            current_layer = 0
            fall_y = 0
            game_over = False


    # Show score in HUD and window title
    score = len(cube_positions)
    draw_hud_score(score)
    glfw.set_window_title(window, f"{WINDOW_TITLE} - Score: {score}")

    glfw.swap_buffers(window)

glfw.terminate()
