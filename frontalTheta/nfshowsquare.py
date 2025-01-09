import pygame
import nfcomm

# Initialize Pygame
pygame.init()

total_width, total_height = 900, 900
screen = pygame.display.set_mode((total_width, total_height))
pygame.display.set_caption("Colored Square Feedback")
running = True
listener =  nfcomm.udpfeedback()
listener.connect()
listener.bindListener()

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            running = False
    col = listener.recievemsg()
    if len( col)==3:
        pygame.draw.rect(screen, (col[0], col[1],col[2]), pygame.Rect( 100, 100, total_width-200, total_height-200))
        pygame.display.flip()
        
pygame.quit()
listener.close()