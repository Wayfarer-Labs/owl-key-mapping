PROMPT_1 = """
We have a dataset of video games + controls. We are going to use this to downstream train a
diffusion world model that generates video games from previous frames + controls.
It's important that we have labels for the controls in terms of what they do, and not just
the raw keybind/button, since these things vary across game and across user.  
We will give you a sequence of clips in which a singular key was pressed, along with an overlay
showing specific keys and their active status. I will briefly explain this overlay.

Firstly, there will boxes correpsonding to mouse buttons (i.e. LMB, RMB, the side buttons, etc.)
The boxes will have numerical labels, rather than semantic (i.e. it will say 0, 1, 2, ... not LMB, RMB, etc.) 
Note that it's pretty common to use non LMB/RMB in games for alt actions when you have side buttons on the mouse.
These boxes will appear, as a row, above another row of boxes which themselves correspond to keyboard buttons.  
Again, these will also be numerical and not have their ascii values. 
In a video, boxes will turn green when the corresponding button/key is pressed.

We want to get labels for the controls in every video. This can be thought of as a mapping for:
mouse: {0 : 'fire', '1' : 'aim', '4' : 'crouch'}
keyboard: {87 : 'forward', 83 : 'backward', 65 : 'left', 68 : 'right', 82 : 'reload'}
Note that keycodes are 'like' ASCII but sometimes they aren't (this is an idiosyncracy of our input tracking software). Just view them as arbitrary numerical labels for simplicity.
Note that in some cases a single key/button might lead to different actions. We are most interested in the 'main' actions in that video.
I.e. if it's an FPS game where 'fire' shoots the gun, but in a menu it might 'click', we care only about the primary 'fire' action, since menus will be clipped out anyways.
In cases where a key has different important functions when tapped/long pressed, you should also focus on the most logical label,
i.e. in some games tapping/holding the crouch button controls sliding/prone/crouch but you can focus on the most natural label, in this case 'crouch'.

You will be given several clips that highlight instances where a specific key was pressed. 
We will also give you some metadata on the game (the exe name, which might tell you what game it is, but not always), as well as the specific key being pressed.
We will attempt to isolate it so that in said clip, *only* that key was pressed, but there might be instances where this is not possible,
at which point you will have to use some deductive reasoning.

You should output in a strict json format:
{
    "reasoning" : [your thinking for the key/button in question and what you think it maps to],
    "action" : [the action you believe this key/button maps to]
}

Make sure your label for an action is as generic as possible, such that when your memory is cleared,
and you are asked to label a new game with a similar action, the label you come up with should line up.
i.e. we don't want "walk forward", "move forward", "run forward" etc. Use the most generic label possible.
In the above case "move forward". Some other examples of generic labels are:
"open menu", "move backward", "equip shotgun", "fire", "aim", "reload", "jump".

There are some instances of bad data where users alt tab and just start typing on their keyboard.
In this case you will see a flurry of different key presses but nothing happening on the screen. 
If you are ever asked to label a key/button and this is the case, write "null" for the action.

Since we're interested in labelling game actions primarily while in-game, menus are irrelevant. 
If you see a menu, ignore it when labelling. If all samples you are given are in menus, write "null" for the action.

If there are instances where its clear the user was typing something in some of the presented windows,
but the game action is clear in others, just output the game action.
""".strip()