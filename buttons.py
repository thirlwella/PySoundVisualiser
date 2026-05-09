# Engine for re-use in other games

import pygame.freetype
import math
import os
import sys

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class Theme:
    def __init__(self, custom_colors=None):
        # Default font size and colors
        self.size = 14
        self.my_ft_font = pygame.freetype.SysFont("Consolas", self.size)
        
        self.font_colour = (255, 255, 255)
        self.colour = (45, 45, 45)
        self.colour_on = (0, 120, 215)
        self.border = 1
        self.border_colour = (100, 100, 100)
        self.header_text_color = (255, 255, 255)
        self.header_background = (0, 120, 215)

        # Apply custom colors if provided
        if custom_colors:
            if "font_colour" in custom_colors:
                self.font_colour = custom_colors["font_colour"]
            if "colour" in custom_colors:
                self.colour = custom_colors["colour"]
            if "colour_on" in custom_colors:
                self.colour_on = custom_colors["colour_on"]
            if "border_colour" in custom_colors:
                self.border_colour = custom_colors["border_colour"]
            if "header_text_color" in custom_colors:
                self.header_text_color = custom_colors["header_text_color"]
            if "header_background" in custom_colors:
                self.header_background = custom_colors["header_background"]
            if "dialogue_font_size" in custom_colors:
                self.size = custom_colors["dialogue_font_size"]
            if "font" in custom_colors:
                self.my_ft_font = custom_colors["font"]
            elif "dialogue_font_size" in custom_colors:
                # If size changed but font wasn't provided, reload default font with new size
                self.my_ft_font = pygame.freetype.SysFont("Consolas", self.size)

class Button:

    #button details provided, unless you overwrite you get default for the style
    def __init__(self, surface, text, text_return, position_x, position_y, button_width,
                 button_height, style=None, size = 12, hidden = False, border = None, custom_colors=None):

        self.theme = Theme(custom_colors)
        self.position_x = position_x
        self.position_y = position_y
        self.text = text
        self.text_return = text_return
        self.font_size = self.theme.size
        self.relative_x = self.position_x / self.font_size
        self.relative_y = self.position_y / self.font_size
        self.colour = self.theme.colour
        self.colour_on = self.theme.colour_on
        self.button_width = button_width
        self.button_height = button_height
        self.active = False
        self.surface = surface
        self.font_colour = self.theme.font_colour
        #Border can be overwritten
        if border == None:
            self.border = self.theme.border
        else:
            self.border = border
        self.border_colour = self.theme.border_colour
        self.style = style
        self.over = False
        self.hidden = hidden
        self.my_ft_font = self.theme.my_ft_font
        self.button_colour = self.colour
        if self.text_return == "text" or self.text_return == "header":
            self.text_position_x = self.position_x
            #self.text_position_y = self.position_y + (self.button_height - self.font_size)
            self.text_position_y = self.position_y + (self.button_height / 2) - (
                self.my_ft_font.get_rect(self.text, size=self.font_size)[3]) / 2

        else:
            #if text is too big it will print as many characters as it can fit
            self.text_length = self.my_ft_font.get_rect(self.text, size=self.font_size)
            while self.text_length.width >= self.button_width:
                self.text =  self.text[:-1]
                self.text_length = self.my_ft_font.get_rect(self.text, size=self.font_size)

            self.text_position_x = self.position_x + (self.button_width / 2) - (
                self.my_ft_font.get_rect(self.text, size=self.font_size)[2]) / 2
            self.text_position_y = self.position_y + (self.button_height / 2) - (
                self.my_ft_font.get_rect(self.text, size=self.font_size)[3]) / 2



        #print("Test_Length", text_length)
        #pygame.draw.rect(self.surface, self.colour, (position_x, position_y, self.button_width, self.button_height))
        #self.my_ft_font.render_to(self.surface, (text_position_x, text_position_y), self.text, self.font_colour)

        #self.button_draw()


    def button_switch(self):
        if not self.hidden:
            if self.active == False:
                self.button_colour = self.colour_on
                self.active = True
            else:
                self.button_colour = self.colour
                self.active = False
            self.button_draw()

    def button_highlight(self):
        if not self.hidden:
            if self.over == True:
                self.button_colour = self.colour_on
                self.active = True
            else:
                self.button_colour = self.colour
                self.active = False
            self.button_draw()

    def button_draw(self):
        if not self.hidden:
            pygame.draw.rect(self.surface, self.button_colour,
                                 (self.position_x, self.position_y, self.button_width, self.button_height), 0, 0)
            if self.border != 0:
                #needs to be offset as borders surrounds (not part of button)
                pygame.draw.rect(self.surface, self.border_colour,
                                 (self.position_x - self.border, self.position_y - self.border,
                                  self.button_width + self.border + self.border,
                                  self.button_height + self.border + self.border), self.border, 0)

            # print("Test_Length", text_length)
            self.my_ft_font.render_to(self.surface, (self.text_position_x, self.text_position_y), self.text, self.font_colour)

    def check_if_pressed(self, position):
        if not self.hidden:
            if position[0] > self.position_x  and \
                    position[0] <= self.position_x + self.button_width  and \
                    position[1] > self.position_y  and \
                    position[1] <= self.position_y + self.button_height:
                self.button_switch()

    def check_if_over(self, position):
        if not self.hidden:
            if position[0] > self.position_x and \
                    position[0] <= self.position_x + self.button_width and \
                    position[1] > self.position_y and \
                    position[1] <= self.position_y + self.button_height:
                self.over = True
                self.button_highlight()
            else:
                self.over = False
                self.button_highlight()
        else:
            self.over = False

    def recalculate(self):
        self.position_x = self.font_size * self.relative_x
        self.position_y = self.font_size * self.relative_y

    def move(self, dx, dy):
        self.position_x += dx
        self.position_y += dy
        self.calc_text_position()

    def calc_text_position(self):
        # Calculates the text position if you have moved a button
        if self.text_return == "text" or self.text_return == "header":
            self.text_position_x = self.position_x
            #self.text_position_y = self.position_y + (self.button_height - self.font_size)
            self.text_position_y = self.position_y + (self.button_height / 2) - (
                self.my_ft_font.get_rect(self.text, size=self.font_size)[3]) / 2
        else:
            self.text_position_x = self.position_x + (self.button_width / 2) - (
                self.my_ft_font.get_rect(self.text, size=self.font_size)[2]) / 2
            self.text_position_y = self.position_y + (self.button_height / 2) - (
                self.my_ft_font.get_rect(self.text, size=self.font_size)[3]) / 2

class Text:
    # Creates a Text object using the screen sizes (x - horizontal, y - virtical position)
    def __init__(self, surface, text, position_x, position_y, colour, background_colour, font_size, font_scale = 1, hidden = False, custom_colors=None):
        self.font_scale = font_scale
        self.size = font_size * font_scale
        self.x = position_x
        self.y = position_y
        self.position_x = position_x * self.size
        self.position_y = position_y * self.size
        self.text = text
        self.colour = colour
        self.background_colour = background_colour
        #self.background_colour = None
        self.surface = surface
        if custom_colors and "font" in custom_colors:
            self.my_ft_font_text = custom_colors["font"]
        else:
            self.my_ft_font_text = pygame.freetype.SysFont("Consolas", int(self.size))
        self.text_length = self.my_ft_font_text.get_rect(self.text)
        self.hidden = hidden

    def text_draw(self):
        # Draw the background color
        #pygame.draw.rect(self.surface, self.background_colour,
         #                    (self.position_x, self.position_y, self.text_length.width, self.text_length.height), 0, 0)

        # print("Test_Length", text_length)
        if self.hidden == False:
            self.my_ft_font_text.render_to(self.surface, (self.position_x, self.position_y),
                                       self.text, self.colour, self.background_colour, size=self.size)

    def recalculate(self):
        # Recalculate when the screen changes
        self.position_x = self.x * self.size
        self.position_y = self.y * self.size

class Text_entry:
    # need to come back to this to make more sophisticated.. but maybe no
    def __init__(self,  text_button):

        self.text_button = text_button
        self.text_button.active = True
        self.typed = ""


        self.input_text()

    def input_text(self):
        entry = True
        clock = pygame.time.Clock()
        self.text_button.text = ""
        while entry:
            events = pygame.event.get()
            clock.tick(30)
            for event in events:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_BACKSPACE:
                        # get text input from 0 to -1 i.e. end.
                        self.text_button.text = self.text_button.text[:-1]
                        self.typed = self.text_button.text
                    elif event.key == pygame.K_RETURN:
                        entry = False
                    else:
                        self.text_button.text += event.unicode
                        self.typed = self.text_button.text
                if event.type == pygame.QUIT:
                    self.typed = "shutdown"
                    entry = False

            self.text_button.button_draw()
            pygame.display.flip()

class Button_sub_loop:
    # This class controls all the buttons
    # the def control is passed the pygame events (only calling them, if it has full control)
    def __init__(self, surface, list_of_buttons, wait_for_reponse = True, need_answer = False, redraw_callback=None):
        self.wait = True
        self.list = list_of_buttons
        self.surface = surface
        self.list_of_choices = []
        self.return_text = None
        self.wait_for_response = wait_for_reponse
        self.need_answer = need_answer
        self.mouse_x_y = (0,0)
        self.redraw_callback = redraw_callback

        for _ in self.list:
            self.list_of_choices.append(_.text)

        self.control()

    def control(self, events = []):
        dialogue = True
        clock = pygame.time.Clock()
        
        # ensure initial redraw
        if self.redraw_callback:
            self.redraw_callback()
        
        if self.wait_for_response:
            for _ in self.list:
                _.button_draw()
            pygame.display.flip()

        while dialogue:
            # If the dialogue has control, then the list will need to be updated
            if self.wait_for_response == True:
                events = pygame.event.get()

            clock.tick(30)
            self.return_text = None
            for event in events:
                position = pygame.mouse.get_pos()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    button_selected = False
                    for d in self.list:
                        d.check_if_over(position)
                        if d.over == True:
                            self.return_text = d.text_return
                            button_selected = True
                            dialogue = False
                    # return blank unless a button has been selected
                    if button_selected == False:
                        self.return_text = "click"
                        # Mouse position if dialogue
                        self.mouse_x_y = (position)
                        if not self.need_answer:
                            dialogue = False
                    else:
                        self.wait_for_response = False

                if event.type == pygame.KEYDOWN:
                    #cycle through the active buttons

                    if event.key == pygame.K_DOWN or event.key == pygame.K_UP:
                        on = 0
                        count = 0
                        visable_list = []
                        for _ in self.list:
                            if not _.hidden:
                                visable_list.append(_)
                        for _ in visable_list:
                            if _.active == True and _.hidden == False:
                                button_was = _
                                button_was.button_switch()
                                on = count
                            count += 1

                        if event.key == pygame.K_DOWN:
                            if on < len(visable_list) - 1:
                                button_is = visable_list[on + 1]
                            else:
                                button_is = visable_list[0]
                            button_is.button_switch()

                        if event.key == pygame.K_UP:
                            if on > 0:
                                button_is = visable_list[on - 1]
                            else:
                                button_is = visable_list[count -1]
                            button_is.button_switch()

                    if event.key == pygame.K_RETURN:
                        #identify the button turned on
                        for _ in self.list:
                            if _.active == True:
                                self.return_text = _.text_return

                        #self.surface.fill((0, 0, 0))
                        dialogue = False

                if event.type == pygame.MOUSEMOTION:
                    #see if the mouse if over any of the buttons
                    last_button = None
                    for _ in self.list:
                        if _.active == True:
                            last_button = _
                    #check for current position
                    now_active = []
                    for _ in self.list:
                        #current_state = _.active
                        #_.check_if_pressed(position)
                        _.check_if_over(position)
                        if _.over == True:
                            now_active.append(_.text_return)
                    # if none highlighted keep last one highlighted
                    # option to turn on
                    keep_last_button_active = False
                    if len(now_active) == 0 and last_button != None and keep_last_button_active == True:
                        last_button.over = True
                        last_button.button_highlight()
                if event.type == pygame.VIDEORESIZE:
                    #pass back to main loop to deal with
                    self.return_text = "resized"
                    self.wait_for_response = False

                if event.type == pygame.QUIT:
                    dialogue = False
                    self.return_text = "shutdown"

            if self.wait_for_response:
                # redraw background/dialogue body
                if self.redraw_callback:
                    self.redraw_callback()
                
                # Redraw buttons/menu if we are waiting for a response
                for _ in self.list:
                    _.button_draw()
                pygame.display.flip()

            if self.wait_for_response == False:
                dialogue = False

    def update(self,surface):
        pygame.event.clear()
        while self.wait:
            event = pygame.event.wait()
            if event.type == pygame.QUIT:
                self.wait = False
                return "finish"
            elif event.type == pygame.KEYDOWN:
                self.wait = False

class Dialogue:
    # Dialogue consists of text message and buttons
    # 'ok' - default, with one button to acknowledge reading
    # 'Yes_No_Cancel' - Answering a question, with option to ignore
    # 'Yes_No' - Answering a question no option to ignore
    def __init__(self, surface, text_header,  text, text_return, style = None, dialogue_type = 'ok', custom_colors=None, redraw_callback=None):
        self.custom_colors = custom_colors
        self.dialogue_theme = Theme(custom_colors)
        self.text = text
        self.text_return = text_return
        self.active = False
        self.surface = surface
        self.background_surface = self.surface.copy
        self.MaxLine = 0
        self.style = style
        self.text_header = text_header
        self.size = self.dialogue_theme.size
        self.my_ft_font = self.dialogue_theme.my_ft_font
        self.font_colour = self.dialogue_theme.font_colour
        self.colour = self.dialogue_theme.colour
        self.colour_on = self.dialogue_theme.colour_on
        self.screen_height = self.surface.get_height()
        self.screen_width = self.surface.get_width()
        self.screenshot = pygame.Surface.copy(self.surface)
        self.redraw_callback = redraw_callback



        # work out the number of lines
        count = 0
        for line in self.text:
            count = count + 1
            test = self.my_ft_font.get_rect(line)[2]
            if self.MaxLine < test:
                self.MaxLine = test
        #Dialogue needs to also accommodate the heading
        test = self.my_ft_font.get_rect(self.text_header)[2]
        if test > self.MaxLine:
            self.MaxLine = test + self.size
        #set dimensions based on text attributes
        self.dialogue_width = self.MaxLine + (self.size * 2)
        #if need to set minimums to allow buttons to render ok
        if dialogue_type == 'yes_no_cancel':
            if self.MaxLine <= (25 * self.size):
                self.dialogue_width = (25 * self.size)
        if dialogue_type == 'yes_no':
            if self.MaxLine <= (15 * self.size):
                self.dialogue_width = (15 * self.size)
        if dialogue_type == 'ok':
            if self.MaxLine <= (6 * self.size):
                self.dialogue_width = (6 * self.size)
        self.dialogue_height = (count + 4) * self.size
        screen_width = self.surface.get_width() / 2
        screen_height = self.surface.get_height() / 2
        self.position_x = screen_width - (self.dialogue_width / 2)
        self.position_y = screen_height - (self.dialogue_height /2)

        self.sub_buttons = []
        # Header as a button
        self.header = Button(self.surface, self.text_header, "header", self.position_x + self.dialogue_theme.border,
                   self.position_y -  self.size * 1.5,
                   self.dialogue_width - (2 * self.dialogue_theme.border), self.size * 1.5, self.style, custom_colors=self.custom_colors)
        # set the header button colour so it does not change
        self.header.colour_on = self.header.colour
        self.header.colour = self.dialogue_theme.header_background
        self.header.button_colour = self.header.colour
        self.header.font_colour = self.dialogue_theme.header_text_color
        
        # Header button X (top right)
        self.close_btn = Button(self.surface, "X", "cancel_dialogue", (self.position_x + self.dialogue_width - self.size - self.dialogue_theme.border),
                   (self.position_y - (self.size * 1.5) ),
                   (self.size ) , self.size * 1.5, self.style, custom_colors=self.custom_colors)

        #need to add options for the type of dialogue
        if dialogue_type == 'ok':
            self.ok()
        if dialogue_type == 'yes_no_cancel':
            self.yes_no_cancel()
        if dialogue_type == 'yes_no':
            self.yes_no()
        
        self.sub_buttons.append(self.header)
        self.sub_buttons.append(self.close_btn)

        # With a dialogue it will take control and wait for button press
        keepgoing = True

        while keepgoing:
            keepgoing = False
            # We need to draw the dialogue body inside the loop if there's a redraw_callback
            def dialogue_redraw():
                if self.redraw_callback:
                    self.redraw_callback()
                self.update_dialogue()

            dialogue = Button_sub_loop(self.surface, self.sub_buttons, need_answer=True, redraw_callback=dialogue_redraw)
            #passing control
            self.text_return = dialogue.return_text
            if self.text_return == "resized":
                self.update_dialogue()
                self.screen_height = self.surface.get_height()
                self.screen_width = self.surface.get_width()
                keepgoing = True
            # check if the top of the dialogue is selected as this will allow you to move
            if self.text_return == "header":
                mouse_position = pygame.mouse.get_pos()
                relative_x =  mouse_position[0] -  self.position_x
                relative_y =  mouse_position[1] -  self.position_y
                mousedown = True
                while mousedown:
                    events = pygame.event.get()
                    for event in events:
                        if event.type == pygame.MOUSEBUTTONUP:
                            mousedown = False
                            keepgoing = True
                    position = pygame.mouse.get_pos()

                    #self.surface.blit(self.screenshot)
                    #ygame.display.blit( self.screenshot, (0,0))
                    self.relocate_dialogue(position, relative_x, relative_y)
                    pygame.display.flip()

    def ok(self):
        # OK just has the one button
        self.sub_buttons = []

        #Add an OK button
        self.sub_buttons.append(Button(self.surface, "OK", "ok", (self.position_x + (self.dialogue_width / 2) - 2 * self.size),
                    (self.position_y + self.dialogue_height - (self.size * 2)),
                     self.size * 4, self.size * 1.5, self.style, custom_colors=self.custom_colors))
        self.active = False

    def yes_no_cancel(self):
        self.sub_buttons = []

        self.sub_buttons.append(
            Button(self.surface, "Yes", "ok", (self.position_x + (self.dialogue_width * 1 / 4) - 6 * self.size),
                   (self.position_y + self.dialogue_height - (self.size * 2)),
                   self.size * 8, self.size * 1.5, self.style, custom_colors=self.custom_colors))
        self.active = False

        self.sub_buttons.append(
            Button(self.surface, "No", "no", (self.position_x + (self.dialogue_width * 2 / 4) - 4 * self.size),
                   (self.position_y + self.dialogue_height - (self.size * 2)),
                   self.size * 8, self.size * 1.5, self.style, custom_colors=self.custom_colors))
        self.active = False

        self.sub_buttons.append(
            Button(self.surface, "Cancel", "cancel_dialogue", (self.position_x +(self.dialogue_width * 3 / 4) - 2 * self.size),
                   (self.position_y + self.dialogue_height - (self.size * 2)),
                   self.size * 8, self.size * 1.5,  self.style, custom_colors=self.custom_colors))
        self.active = False

    def yes_no(self):
        self.sub_buttons = []

        self.sub_buttons.append(
            Button(self.surface, "Yes", "ok", (self.position_x + (self.dialogue_width * 1 / 3) - 3 * self.size),
                   (self.position_y + self.dialogue_height - (self.size * 2)),
                   self.size * 5, self.size * 1.5, self.style, custom_colors=self.custom_colors))
        self.active = False

        self.sub_buttons.append(
            Button(self.surface, "No", "no", (self.position_x + (self.dialogue_width * 2 / 3) - 2 * self.size),
                   (self.position_y + self.dialogue_height - (self.size * 2)),
                   self.size * 5, self.size * 1.5, self.style, custom_colors=self.custom_colors))
        self.active = False


    def update_dialogue(self):
        # solid background
        pygame.draw.rect(self.surface, self.dialogue_theme.colour,
                         (self.position_x, self.position_y, self.dialogue_width, self.dialogue_height), 0, 0)
        #  edging
        pygame.draw.rect(self.surface, self.dialogue_theme.border_colour,
                         (self.position_x, self.position_y, self.dialogue_width, self.dialogue_height), 1, 0)

        # Ensure text is visible by checking font colour vs background colour
        text_color = self.font_colour
        if text_color == self.dialogue_theme.colour:
            # Fallback to white or black if they are same
            if sum(text_color) / 3 > 128:
                text_color = (0, 0, 0)
            else:
                text_color = (255, 255, 255)

        self.text_position_x = self.position_x + (self.dialogue_width / 2) - (self.MaxLine) / 2

        self.text_position_y = self.position_y + self.size
        for line in self.text:
            self.text_position_x = self.position_x + (self.dialogue_width / 2) - (self.my_ft_font.get_rect(line)[2]) / 2
            self.my_ft_font.render_to(self.surface, (self.text_position_x, self.text_position_y), line, text_color)
            self.text_position_y = self.text_position_y + self.size

        for dialogue_button in self.sub_buttons:
            dialogue_button.button_draw()

    def relocate_dialogue(self, xy, rx, ry):
        original_x = self.position_x
        original_y = self.position_y


        self.position_x = xy[0] - rx
        self.position_y = xy[1] - ry

        if self.position_x > 0 and self.position_y - self.size * 1.5 > 0 \
                and self.position_x + self.dialogue_width < self.screen_width \
                and self.position_y + self.dialogue_height < self.screen_height:


            for dialogue_button in self.sub_buttons:
                dialogue_button.position_x  -= original_x - self.position_x
                dialogue_button.position_y  -= original_y - self.position_y
                dialogue_button.text_position_x -= original_x - self.position_x
                dialogue_button.text_position_y -= original_y - self.position_y

            for line in self.text:
                self.text_position_x -= original_x - self.position_x
                self.text_position_y -= original_y - self.position_y

            #Copy background back so movement will work
            self.surface.blit(self.screenshot, (0,0))
            # Redraw the dialogue
            self.update_dialogue()

        else:
            self.position_y = original_y
            self.position_x = original_x

class Menu_List:
    # creates a menu list from a list of choices provided
    # assumption that the list appears when you press button
    # add scroll bar if list is greater than the max list
    def __init__(self, surface, button, list_of_choices, hidden = False, style = None, custom_colors=None):
        self.custom_colors = custom_colors
        self.theme = Theme(custom_colors)
        self.style = style
        self.but = button
        self.surface = surface
        self.list_of_choices = list_of_choices
        self.list = []
        self.scroll_list = []
        self.hidden = hidden
        self.top_item = 1
        #self.draw_list()
        self.scroll_bar_list()
        if self.hidden:
            self.deactivate_list()
        else:
            self.activate_list()

    def draw_list(self):
        # Borders are removed from lists - as currently boarder is not active part of button
        y = self.but.position_y
        firstButton = True
        for _ in self.list_of_choices:
            # offsetting the list from the original button
            x = self.but.position_x + (int(self.but.button_width / 8))
            self.list.append(
                Button(self.surface, _, _, x,y + self.but.button_height,
                       self.but.button_width, self.but.button_height, self.but.style, border=0, hidden=self.hidden, custom_colors=self.custom_colors))
            #self.list.active = False
            y += self.but.button_height

    def scroll_bar_list(self):
        self.list_length = len(self.list_of_choices)
        self.max_length = 3

        # Borders are removed from lists - as currently border is not active part of button
        y = self.but.position_y
        x = self.but.position_x

        #add scroll bar to the top right if needed
        if self.list_length > self.max_length:
            self.scroll_list.append(
                Button(self.surface, '▲','down',  x + self.but.button_width, y,
                       self.theme.size, self.theme.size, self.but.style, border=0, custom_colors=self.custom_colors))
            # add scroll bar button
            self.scroll_list.append(
                Button(self.surface, 'x', 'scroll', x + self.but.button_width, y + self.theme.size,
                       self.theme.size, self.theme.size , self.but.style, border=0, custom_colors=self.custom_colors))

            count = 0
            for _ in self.list_of_choices:
                count += 1
                if count > self.max_length:
                    self.hidden = True
                else:
                    self.hidden = False
                self.list.append(
                    Button(self.surface, _, _, x, y,
                           self.but.button_width, self.but.button_height, self.but.style, border=0, hidden=self.hidden, custom_colors=self.custom_colors))
                y += self.but.button_height

                if count == self.max_length:
                    #add scroll bar to the bottom right
                    self.scroll_list.append(
                    Button(self.surface, '▼','up', x + self.but.button_width, y - self.theme.size,
                           self.theme.size, self.theme.size, self.but.style, border=0, custom_colors=self.custom_colors))
        else:
            # Short list - no scroll bars needed
            for _ in self.list_of_choices:
                self.list.append(
                    Button(self.surface, _, _, x, y,
                           self.but.button_width, self.but.button_height, self.but.style, border=0, hidden=False, custom_colors=self.custom_colors))
                y += self.but.button_height

    def activate_list(self):
        count = 0
        for _ in self.list:
            count += 1
            if self.max_length >= count:
                _.hidden = False
                _.active = True
            _.button_draw()
        for _ in self.scroll_list:
            _.hidden = False
            _.active = True
            _.button_draw()
        pygame.display.flip()

    def deactivate_list(self):
        for _ in self.list:
            _.hidden = True
            _.active = False

        #set back to original locations
        self.top_item = 1

        y = self.but.position_y
        for _ in self.list:
            _.position_y = y
            _.calc_text_position()
            y += _.button_height

        for _ in self.scroll_list:
            _.hidden = True
            _.active = False

    def scroll_up(self):
        if self.top_item <= self.list_length - self.max_length:
            self.top_item += 1
            # Move them all up one space
            count = 0
            for _ in self.list:
                count += 1
                if count >= self.top_item and count < self.top_item + self.max_length:
                    _.hidden = False
                else:
                    _.hidden = True
                _.move(0,-_.button_height)

    def scroll_down(self):
        if self.top_item > 1:
            self.top_item -= 1
            # Move them all up one space
            count = 0
            for _ in self.list:
                count += 1
                if count >= self.top_item and count < self.top_item + self.max_length:
                    _.hidden = False
                else:
                    _.hidden = True
                _.move(0,+_.button_height)

    def like_dialogue(self, redraw_callback=None):
        # wait for a selection, rather than part of the game
        keepgoing = True
        while keepgoing:
            keepgoing = False
            dialogue = Button_sub_loop(self.surface, self.list + self.scroll_list, redraw_callback=redraw_callback)
            self.text_return = dialogue.return_text
            print(self.text_return)
            if self.text_return == "resized":
                keepgoing = True
            if self.text_return == "shutdown":
                keepgoing = False
            #scroll bars
            if self.text_return == "up":
                self.scroll_up()
                keepgoing = True
                self.text_return = None
            if self.text_return == "down":
                self.scroll_down()
                keepgoing = True
                self.text_return = None
            if self.text_return != None:
                self.deactivate_list()

class Background:
    # uses an image as the background and repeats to fill the screen
    # dx and dy can be used to scroll in different direction
    # Probably better to ensure screen size is divisable by background image size (as an integer)
    # Called from scene class
    def __init__(self, surface, speed = 0, direction = 0, image = None):
        # direction 0 is right
        self.direction = direction
        self.speed = speed
        #self.dx = dx
        #self.dy = dy
        self.counter = 10
        if image is None:
            # Create a default surface if no image is provided
            self.image = pygame.Surface((100, 100))
            self.image.fill((20, 20, 50))
        else:
            try:
                self.image = pygame.image.load(resource_path(image)).convert_alpha()
            except (pygame.error, FileNotFoundError):
                # Fallback to default if image file not found
                self.image = pygame.Surface((100, 100))
                self.image.fill((20, 20, 50))
        self.surface = surface
        self.screen_height = self.surface.get_height()
        self.screen_width = self.surface.get_width()
        self.height = self.image.get_height()
        self.width = self.image.get_width()
        #centre of the screen (tile starts here)
        self.x = int((self.screen_width / 2) - (self.width / 2))
        self.y = int((self.screen_height / 2) - (self.height / 2))
        self.tile_limit_max_x = int(self.x + self.width)
        self.tile_limit_max_y = int(self.y + self.height)
        self.tile_limit_min_x = int(self.x - self.width)
        self.tile_limit_min_y = int(self.y - self.height)
        self.calc_dx_dy()

    def update(self):
        #print('self dx',self.dx)
        #need to add way to slow and smooth speeding up
        self.counter -= 1
        self.x += self.dx
        self.y += self.dy
        self.rotate(1)
        if self.counter == 0:
            #self.dx -= 1
            self.counter = 10

        #If background goes out limit, wrap around on that axis
        if self.x > self.tile_limit_max_x:
            self.x -= self.width
        if self.x + self.width < self.tile_limit_min_x:
            self.x += self.width

        if self.y > self.tile_limit_max_y:
            self.y -= self.height
        if self.y + self.height < self.tile_limit_min_y:
            self.y += self.height

        #need to repeat the background image to outside of the screen edge
        for a in range(self.x , self.screen_width + self.width , self.width):
            for b in range(self.y, self.screen_height + self.height, self.height):
                self.surface.blit(self.image, (a, b))
            for b in range(self.y -self.height, -self.height, -self.height):
                self.surface.blit(self.image, (a, b))

        for a in range(self.x - self.width, -self.width, -self.width ):
            for b in range(self.y, self.screen_height + self.height, self.height):
                self.surface.blit(self.image, (a, b))
            for b in range(self.y - self.height, -self.height, -self.height):
                self.surface.blit(self.image, (a, b))

    def calc_dx_dy(self):
        radians = self.direction * math.pi / 180
        dx = self.speed * math.cos(radians)
        dy = self.speed * math.sin(radians) * -1
        #print("dx", dx, "dy", dy)
        self.dx = int(dx)
        self.dy = int(dy)
        #print("dx", self.dx, "dy", self.dy)

    def rotate(self, amt):
        self.direction += amt
        if self.direction > 360:
            self.direction = amt
        if self.direction < 0:
            self.direction = 360 - amt
        self.calc_dx_dy()

class Scene:
    # Set ups screen
    # maybe include theme so no need for 2 classes
    def __init__(self, screen_height, screen_width):
        self.scene_details = pygame.display.set_mode([screen_width, screen_height], pygame.RESIZABLE | pygame.DOUBLEBUF, 8)
        self.text_rows = 30
        self.text_columns = 40
        self.background = Background(self.scene_details, 5, 90)
        self.background2 = Background(self.scene_details, 7, 90)
        self.background3 = Background(self.scene_details, 9, 90)

    def screen_resize(self):
        # Do not want to break the screen ratio of 3:2 so need to resize back to this
        self.screen_width = self.scene_details.get_width()
        self.screen_height = self.scene_details.get_height()
        self.width = int(self.screen_width / self.text_columns)
        self.height = int(self.screen_height / self.text_rows)
        self.font_size = min(self.width, self.height)
        self.screen_width = self.font_size * self.text_columns
        self.screen_height = self.font_size * self.text_rows
        self.background.screen_width= self.screen_width
        self.background.screen_height = self.screen_height
        self.background2.screen_width = self.screen_width
        self.background2.screen_height = self.screen_height
        self.background3.screen_width = self.screen_width
        self.background3.screen_height = self.screen_height
        self.scene_details = pygame.display.set_mode([self.screen_width, self.screen_height],
                                              pygame.RESIZABLE | pygame.DOUBLEBUF, 8)

    def switch(self, object_list, matching ):
        # This is used for buttons or Text to switch property of visible or not
        for _ in object_list:
            if _.text == matching:
                if _.hidden == True:
                    _.hidden = False
                else:
                    _.hidden = True
