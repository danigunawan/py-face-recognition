import glob
import os
import time
from multiprocessing.pool import ThreadPool

import cv2
import imutils
import numpy as np
from retina_face.retinaface import RetinaFace
from arc_face.face_recognition import FaceRecognition

# count = 1

# detector = RetinaFace(retina_face_model, 0, 0, 'net3')

# test_img = './test_data/weeding.jpg'
from arc_face import preprocessor

FONT = cv2.FONT_HERSHEY_SIMPLEX


def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        if 'log_time' in kw:
            name = kw.get('log_name', method.__name__.upper())
            kw['log_time'][name] = int((te - ts) * 1000)
        else:
            print('%r  %2.2f ms' % (method.__name__, (te - ts) * 1000))
        return result

    return timed


def drawText(image, text, x1, y1):
    font_scale = 0.55
    margin = 5
    thickness = 2
    color = (255, 255, 255)

    size = cv2.getTextSize(text, FONT, font_scale, thickness)

    text_width = size[0][0]
    text_height = size[0][1]
    line_height = text_height + size[1] + margin

    x = image.shape[1] - margin - text_width
    y = margin + size[0][1] + line_height

    cv2.putText(image, text, (x1, y1), FONT, font_scale, color, thickness)


class FaceDetector:
    thresh = 0.8
    scales = [720, 1920]
    retina_face_model = os.path.abspath('models/retinaface-R50/R50')
    # retina_face_model = os.path.abspath('models/retinaface-R50/R50-0000')
    arc_face_model = os.path.abspath('models/model-r100-arcface-ms1m-refine-v2/model-r100-ii/model-0000')

    def __init__(self):
        self.__embeddings = []

    def __enter__(self):
        self.face_detector = RetinaFace(self.retina_face_model, 0, 0, 'net3')
        self.recognizer = FaceRecognition(self.arc_face_model)
        # self.face_detector.prepare(0)
        self.recognizer.prepare(0)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        del self.recognizer
        del self.face_detector

    def init_embeddings(self, img_path):
        train_images = []
        for f in glob.glob('{}/*.jpg'.format(img_path)):
            train_images.append(f)

        for im_path in train_images:
            self.get_emb(im_path)


    def get_emb(self, im_path):
        # read image from file
        img = cv2.imread(im_path)

        # detect faces
        faces, landmarks = self.pre_process_img(img)

        # extract rect and landmark=5
        box = faces[0].astype(np.int)
        landmark5 = landmarks[0].astype(np.float32)

        # x1, y1, x2, y2 = box[0], box[1], box[2], box[3]
        # ch = y2 - y1
        # cw = x2 - x1
        # org_img = img.copy()
        # crop_img = org_img[y1:y1 + ch, x1:x1 + cw]
        # cv2.imshow('Crop', crop_img)
        # cv2.waitKey(0)
        #
        #
        # crop_img = cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB)
        # crop_img = cv2.resize(crop_img, (112, 112))
        # # crop_img = preprocessor.preprocess(crop_img, landmark=landmark5, image_size=[112,112])
        # crop_img = preprocessor.preprocess(crop_img, image_size=[112, 112])

        # preprocess face before get embeddings
        crop_img = self.pre_process_face(img, box, landmark5)
        emb = self.recognizer.get_embedding(crop_img)
        # emb = self.recognizer.get(crop_img, landmark5)

        v = im_path.split('/')[-1].replace('.jpg', '')
        self.__embeddings.append((emb.copy(), v))

        del crop_img
        del box
        del landmark5
        del emb
        del img

    def pre_process_img(self, img):
        try:
            # get image shape
            im_shape = img.shape

            target_size, max_size = self.scales
            im_size_min = np.min(im_shape[0:2])
            im_size_max = np.max(im_shape[0:2])

            # if im_size_min>target_size or im_size_max>max_size:
            im_scale = float(target_size) / float(im_size_min)
            # prevent bigger axis from being more than max_size:
            if np.round(im_scale * im_size_max) > max_size:
                im_scale = float(max_size) / float(im_size_max)

            print('im_scale', im_scale)
            faces, landmarks = self.face_detector.detect(img, self.thresh, scales=[im_scale], do_flip=False)

            return faces, landmarks
        except Exception as x:
            print(x)

    def pre_process_face(self, img, box, landmark5):
        try:

            x1, y1, x2, y2 = box[0], box[1], box[2], box[3]

            ch = y2 - y1
            cw = x2 - x1
            margin = 0
            bb = np.zeros(4, dtype=np.int32)
            bb[0] = np.maximum(x1 - margin / 2, 0)
            bb[1] = np.maximum(y1 - margin / 2, 0)
            bb[2] = np.minimum(x2 + margin / 2, img.shape[1])
            bb[3] = np.minimum(y2 + margin / 2, img.shape[0])
            # ret = img[bb[1]:bb[3], bb[0]:bb[2], :]
            ret = img[bb[1]:bb[3], bb[0]:bb[2], :]

            lan = [[l[0] - bb[0], l[1] - bb[1]] for l in landmark5]
            ln = np.array(lan, dtype=np.float32)
            # print(lan)



            # wr = ret.copy()
            # # for l in range(landmark5.shape[0]):
            # for l in range(ln.shape[0]):
            #     color = (0, 0, 255)
            #     if l == 0 or l == 3:
            #         color = (0, 255, 0)
            #     # cv2.circle(wr, (landmark5[l][0], landmark5[l][1]), 1, color, 2)
            #     cv2.circle(wr, (ln[l][0], ln[l][1]), 1, color, 2)





            # cv2.imshow('Images', wr)

            # Hit 'q' on the keyboard to quit!
            # cv2.waitKey(0)


            crop_img = preprocessor.preprocess(ret, image_size=[112, 112], landmark=ln)
            crop_img = cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB)
            # crop_img = cv2.resize(crop_img, (112, 112))

            # cv2.imshow('Images', crop_img)

            # Hit 'q' on the keyboard to quit!
            # cv2.waitKey(0)


            return crop_img
        except Exception as x:
            print(x)

    def process_images(self, image_path):

        print(image_path)

        # read image from file
        img = cv2.imread(image_path)

        # # get image shape
        im_shape = img.shape

        # cv2.imshow('Images', img)
        #
        # # Hit 'q' on the keyboard to quit!
        # cv2.waitKey(0)

        orig_img = img.copy()

        resized = imutils.resize(orig_img, height=720)
        r_shape = resized.shape
        #
        # target_size, max_size = self.scales
        # im_size_min = np.min(im_shape[0:2])
        # im_size_max = np.max(im_shape[0:2])
        #
        # # if im_size_min>target_size or im_size_max>max_size:
        # im_scale = float(target_size) / float(im_size_min)
        # # prevent bigger axis from being more than max_size:
        # if np.round(im_scale * im_size_max) > max_size:
        #     im_scale = float(max_size) / float(im_size_max)
        #
        # print('im_scale', im_scale)

        # faces, landmarks = self.face_detector.detect(img, self.thresh, scales=[im_scale], do_flip=False)
        faces, landmarks = self.pre_process_img(img)

        if faces.any():
            print('find', faces.shape[0], 'faces')
            for i in range(faces.shape[0]):
                # print('score', faces[i][4])
                box = faces[i].astype(np.int)

                x1, y1, x2, y2 = box[0], box[1], box[2], box[3]
                # org_img = img.copy()
                # crop_img = org_img[y1:y1 + ch, x1:x1 + cw]
                #
                # # cv2.imshow('Images', crop_img)
                #
                # # Hit 'q' on the keyboard to quit!
                # # cv2.waitKey(0)
                #
                # # face_list.append(crop_img)
                # crop_img = cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB)
                # rimg = cv2.resize(crop_img, (112, 112))

                landmark5 = landmarks[i].astype(np.float32)
                crop_img = self.pre_process_face(img, box, landmark5)


                emb = self.recognizer.get_embedding(crop_img)

                results = [(self.recognizer.compute_match(emb, c[0]), c[1]) for c in self.__embeddings]
                index = np.argmax([d[0] for d in results])
                dis = results[index]
                print(dis)
                # # cv2.putText(img, dis[1], (x1, y1), FONT, 0.55, (255, 255, 255), 2)
                # drawText(img, '{} - {:.2f} %'.format(dis[1], dis[0] * 100), x1, y1)

                # if dis[0] >= 0.5:
                #     continue





                # text = '{} : {} %'.format(dis[1], round((dis[0] * 100), 1))
                x01, x02, y01, y02 = x1 / im_shape[1], x2 / im_shape[1], y1 / im_shape[0], y2 / im_shape[0]

                rx01, rx02, ry01, ry02 = x01 * r_shape[1], x02 * r_shape[1], y01 * r_shape[0], y02 * r_shape[0]

                rx01, rx02, ry01, ry02 = int(rx01), int(rx02), int(ry01), int(ry02)

                text = '{}'.format(dis[1])
                print(text)
                size = cv2.getTextSize(text, FONT, 0.55, 2)
                # color = (255,0,0)
                color = (0, 0, 255)
                # cv2.rectangle(orig_img, (x1, y1), (x2, y2), color, 2)
                # # Draw a label with a name below the face
                # cv2.rectangle(orig_img, (x1, y2), (x1 + size[0][0] + 6, y2 + size[0][1] + 6), (0, 0, 255), cv2.FILLED)
                #
                # cv2.putText(orig_img, text, (x1 + 6, y2 + size[0][1]), FONT, 0.55, (255, 255, 255), 2)


                cv2.rectangle(resized, (int(rx01), int(ry01)), (int(rx02), int(ry02)), color, 2)
                if dis[0] < 0.35:
                    continue
                # Draw a label with a name below the face
                cv2.rectangle(resized, (rx01, ry02), (rx01 + size[0][0] + 6, ry02 + size[0][1] + 6), (0, 0, 255), cv2.FILLED)

                cv2.putText(resized, text, (rx01 + 6, ry02 + size[0][1]), FONT, 0.55, (255, 255, 255), 2)





                # print(landmark.shape)
                # for l in range(landmark5.shape[0]):
                #     color = (0, 0, 255)
                #     if l == 0 or l == 3:
                #         color = (0, 255, 0)
                #     cv2.circle(img, (landmark5[l][0], landmark5[l][1]), 1, color, 2)

        cv2.imwrite('output_data/{}'.format(image_path.split('/')[-1]), orig_img)

        # print(im_shape)
        # w, h = im_shape[1], im_shape[0]
        # if h > 720:
        #     img = imutils.resize(img, height=720)
        cv2.imshow('Images', resized)

        # Hit 'q' on the keyboard to quit!
        cv2.waitKey(0)

    def process_frames(self, img):
        # get image shape
        im_shape = img.shape

        target_size, max_size = self.scales
        im_size_min = np.min(im_shape[0:2])
        im_size_max = np.max(im_shape[0:2])

        # if im_size_min>target_size or im_size_max>max_size:
        im_scale = float(target_size) / float(im_size_min)
        # prevent bigger axis from being more than max_size:
        if np.round(im_scale * im_size_max) > max_size:
            im_scale = float(max_size) / float(im_size_max)

        print('im_scale', im_scale)

        faces, landmarks = self.face_detector.detect(img, self.thresh, scales=[im_scale], do_flip=False)

        if faces.any():
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

            cv2.imshow('Images', img)


@timeit
def recognize_images():
    # # read image from file
    # img = cv2.imread('test_data/rahat1.jpg')
    # img = imutils.resize(img, 112, 112)
    # fr = FaceRecognizer()
    # fr.process_img(img)
    # return
    with FaceDetector() as face_rec:
        face_rec.init_embeddings('train_data/')
        test_images = []
        # p = 'test_data/many_faces1.jpg'
        p = 'test_data/*.jpg'
        for f in glob.glob(p):
            test_images.append(f)

        for im in test_images:
            try:
                face_rec.process_images(im)
            except Exception as x:
                print(x)

            # break

        # with ThreadPool(1) as pool:
        #     pool.map(face_rec.process_images, test_images)

    cv2.destroyAllWindows()


def recognize_from_webcam():
    webcam = cv2.VideoCapture(0)
    with FaceDetector() as face_detector:
        while True:
            # Grab a single frame of video
            ret, frame = webcam.read()

            face_detector.process_frames(frame)

            # Hit 'q' on the keyboard to quit!
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break


if __name__ == '__main__':
    recognize_images()
    # recognize_from_webcam()
