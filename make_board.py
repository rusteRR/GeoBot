from PIL import Image


def create_board(path):
    im1 = Image.open(path)
    im2 = Image.open('board.jpg')
    im1 = im1.convert('RGB')
    im2 = im2.convert('RGB')
    im2.paste(im1, (0, 170, 600, 620))
    im2.save('result.jpg')
