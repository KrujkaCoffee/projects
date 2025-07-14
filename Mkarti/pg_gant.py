import pygame
import project_cust_38.Cust_Functions as F
from os import path

pygame.init()
START_Y = 5
START_X = 5
FPS = 30
HEIGHT_LINE = 4
WIGHT_LINE = 3
SHAG = 10
DICT_COLOUR = {'Прогресс_0101': (255, 192, 0),
               'Прогресс_0102': (0, 176, 80),
               'Прогресс_0103': (0, 112, 192),
               'Прогресс_0104': (165, 165, 165),
               'white': (255, 255, 255),
               'grey': (50, 50, 50),
               'blue': (155, 155, 255)
               }

SPIS_MK = F.load_file('mkards.txt')
LEN_MK = len(SPIS_MK) - 1


def paint_gant(sc, SPIS_MK):
    sc.fill(DICT_COLOUR['grey'])
    y = START_Y
    for i in range(1, len(SPIS_MK)):
        x = START_X
        for j in range(len(SPIS_MK[i])):
            if SPIS_MK[0][j] in DICT_COLOUR:
                summ, val = SPIS_MK[i][j].split("$")
                width_rect = int(val) / WIGHT_LINE
                contur_rect = int(summ) / WIGHT_LINE
                pygame.draw.rect(sc, DICT_COLOUR[SPIS_MK[0][j]], (x, y, width_rect, HEIGHT_LINE))
                pygame.draw.rect(sc, DICT_COLOUR["white"], (x, y, contur_rect, HEIGHT_LINE), 1)
                x += int(summ) / WIGHT_LINE
        y += HEIGHT_LINE + 0.5


sc = pygame.display.set_mode((600, LEN_MK * (HEIGHT_LINE + 0.5)), pygame.RESIZABLE)  # размер дисплея

pygame.display.set_caption('План работ производства')
pygame.display.set_icon(pygame.image.load(path.join("icons", "icon.png")))
clock = pygame.time.Clock()  # экзепляр часов

paint_gant(sc, SPIS_MK)
pygame.display.update()
fl_Running = True  # флаг продолжения цикла опроса событий
fl_right = False
fl_left = False
fl_up = False
fl_down = False

first_pos_selection = None
surf_selection = None
while True:
    if fl_Running == False:
        break
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            fl_Running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            buttons = pygame.mouse.get_pressed()
            print(buttons)
            if event.button == 4:  # mouse_up
                if buttons[2]:  # RMB
                    START_X += SHAG * 10
                else:
                    HEIGHT_LINE += SHAG / 5
            if event.button == 5:  # mouse_down
                if buttons[2]:  # RMB
                    START_X -= SHAG * 10
                else:
                    if HEIGHT_LINE > SHAG / 5:
                        HEIGHT_LINE -= SHAG / 5
            pygame.mouse.get_rel()
            if buttons[0]:
                first_pos_selection = pygame.mouse.get_pos()
            surf_selection = None
        if event.type == pygame.MOUSEBUTTONUP:
            surf_selection = None
        if event.type == pygame.MOUSEMOTION:
            buttons = pygame.mouse.get_pressed()
            if buttons[1]:  # movie scene
                delt_x, delt_y = pygame.mouse.get_rel()
                START_X += delt_x
                START_Y += delt_y
            if buttons[0]:  # selection
                if first_pos_selection != None:
                    second_x, second_y = pygame.mouse.get_pos()
                    delt_x = second_x - first_pos_selection[0]
                    delt_y = second_y - first_pos_selection[1]
                    if delt_x > 0 and delt_y > 0:
                        surf_selection = pygame.Surface((delt_x, delt_y))
                        surf_selection.fill(DICT_COLOUR['blue'])
                        surf_selection.set_alpha(40)
    if fl_Running:
        keys = pygame.key.get_pressed()
        if keys[pygame.K_RIGHT]:
            START_X += SHAG
        if keys[pygame.K_LEFT]:
            START_X -= SHAG
        if keys[pygame.K_DOWN]:
            START_Y += SHAG
        if keys[pygame.K_UP]:
            START_Y -= SHAG
        paint_gant(sc, SPIS_MK)
        if surf_selection != None:
            sc.blit(surf_selection, first_pos_selection)
        pygame.display.update()
    clock.tick(FPS)  # FPS
