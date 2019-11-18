import cv2
import numpy as np
from retina_face.retinaface import RetinaFace

retina_face_model = 'models/retinaface-R50/R50'

thresh = 0.8
scales = [1280, 1980]

count = 1

detector = RetinaFace(retina_face_model, 0, 0, 'net3')

test_img = './test_data/weeding.jpg'

img = cv2.imread(test_img)
print(img.shape)
im_shape = img.shape
target_size = scales[0]
max_size = scales[1]
im_size_min = np.min(im_shape[0:2])
im_size_max = np.max(im_shape[0:2])
# im_scale = 1.0
# if im_size_min>target_size or im_size_max>max_size:
im_scale = float(target_size) / float(im_size_min)
# prevent bigger axis from being more than max_size:
if np.round(im_scale * im_size_max) > max_size:
    im_scale = float(max_size) / float(im_size_max)

print('im_scale', im_scale)

scales = [im_scale]
flip = False

for c in range(count):
    faces, landmarks = detector.detect(img, thresh, scales=scales, do_flip=flip)
    print(c, faces.shape, landmarks.shape)

if faces is not None:
    print('find', faces.shape[0], 'faces')
    for i in range(faces.shape[0]):
        # print('score', faces[i][4])
        box = faces[i].astype(np.int)
        # color = (255,0,0)
        color = (0, 0, 255)
        cv2.rectangle(img, (box[0], box[1]), (box[2], box[3]), color, 2)
        if landmarks is not None:
            landmark5 = landmarks[i].astype(np.int)
            # print(landmark.shape)
            for l in range(landmark5.shape[0]):
                color = (0, 0, 255)
                if l == 0 or l == 3:
                    color = (0, 255, 0)
                cv2.circle(img, (landmark5[l][0], landmark5[l][1]), 1, color, 2)

    filename = './detector_test.jpg'
    print('writing', filename)
    cv2.imwrite(filename, img)
    cv2.imshow('Images', img)

    cv2.waitKey(0)
cv2.destroyAllWindows()