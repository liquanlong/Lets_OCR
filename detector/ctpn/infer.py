import cv2
import numpy as np
import os
import copy
import lib.dataset_handler
import torch
import Net.net as Net
import lib.utils
import lib.draw_image
import lib.nms
import math
import random
import shutil
import sys
anchor_height = [11, 16, 22, 32, 46, 66, 94, 134, 191, 273]

IMG_ROOT = "/home/ljs/ctpn_torch/dataset/OCR_dataset/ctpn/test_im"
GT_ROOT = "/home/ljs/ctpn_torch/dataset/OCR_dataset/ctpn/test_gt"
TEST_RESULT = './test_result'


def gen_test_images(gt_root, img_root, test_num=10):
    img_list = os.listdir(img_root)
    random_list = random.sample(img_list, test_num)
    test_pair = []
    for im in random_list:
        name, _ = os.path.splitext(im)
        gt_name = 'gt_' + name + '.txt'
        gt_path = os.path.join(gt_root, gt_name)
        im_path = os.path.join(img_root, im)
        test_pair.append((im_path, gt_path))
    return test_pair


def infer_one(im_name, net):
    im = cv2.imread(im_name)
    im = lib.dataset_handler.scale_img_only(im)
    img = copy.deepcopy(im)
    img = img.transpose(2, 0, 1)
    img = img[np.newaxis, :, :, :]
    img = torch.Tensor(img)
    v, score, side = net(img, val=True)
    result = []
    for i in range(score.shape[0]):
        for j in range(score.shape[1]):
            for k in range(score.shape[2]):
                if score[i, j, k, 1] > 0.7:
                    result.append((j, k, i, float(score[i, j, k, 1].detach().numpy())))

    for_nms = []
    for box in result:
        pt = lib.utils.trans_to_2pt(box[1], box[0] * 16 + 7.5, anchor_height[box[2]])
        for_nms.append([pt[0], pt[1], pt[2], pt[3], box[3], box[0], box[1], box[2]])
    for_nms = np.array(for_nms, dtype=np.float32)
    nms_result = lib.nms.cpu_nms(for_nms, 0.3)

    for i in nms_result:
        vc = v[int(for_nms[i, 7]), 0, int(for_nms[i, 5]), int(for_nms[i, 6])]
        vh = v[int(for_nms[i, 7]), 1, int(for_nms[i, 5]), int(for_nms[i, 6])]
        cya = for_nms[i, 5] * 16 + 7.5
        ha = anchor_height[int(for_nms[i, 7])]
        cy = vc * ha + cya
        h = math.pow(10, vh) * ha
        lib.draw_image.draw_box_2pt(im, for_nms[i, 0:4])
    cv2.imwrite('infer_'+im_name, im)

def random_test(net):
    test_pair = gen_test_images(GT_ROOT, IMG_ROOT, 50)
    print(test_pair)
    if os.path.exists(TEST_RESULT):
        shutil.rmtree(TEST_RESULT)

    os.mkdir(TEST_RESULT)

    for t in test_pair:
        im = cv2.imread(t[0])
        gt = lib.dataset_handler.read_gt_file(t[1])
        im, gt = lib.dataset_handler.scale_img(im, gt)
        img = copy.deepcopy(im)
        img = img.transpose(2, 0, 1)
        img = img[np.newaxis, :, :, :]
        img = torch.Tensor(img)
        v, score, side = net(img, val=True)
        result = []
        for i in range(score.shape[0]):
            for j in range(score.shape[1]):
                for k in range(score.shape[2]):
                    if score[i, j, k, 1] > 0.7:
                        result.append((j, k, i, float(score[i, j, k, 1].detach().numpy())))

        for_nms = []
        for box in result:
            pt = lib.utils.trans_to_2pt(box[1], box[0] * 16 + 7.5, anchor_height[box[2]])
            for_nms.append([pt[0], pt[1], pt[2], pt[3], box[3], box[0], box[1], box[2]])
        for_nms = np.array(for_nms, dtype=np.float32)
        nms_result = lib.nms.cpu_nms(for_nms, 0.3)

        for i in nms_result:
            vc = v[int(for_nms[i, 7]), 0, int(for_nms[i, 5]), int(for_nms[i, 6])]
            vh = v[int(for_nms[i, 7]), 1, int(for_nms[i, 5]), int(for_nms[i, 6])]
            cya = for_nms[i, 5] * 16 + 7.5
            ha = anchor_height[int(for_nms[i, 7])]
            cy = vc * ha + cya
            h = math.pow(10, vh) * ha
            lib.draw_image.draw_box_2pt(im, for_nms[i, 0:4])
            #im = other.draw_box_h_and_c(im, int(for_nms[i, 6]), cy, h)

        # print(result)
        #for box in result:
         #   im = other.draw_box_h_and_c(im, box[1], box[0] * 16 + 7.5, anchor_height[box[2]])

        for gt_box in gt:
            im = lib.draw_image.draw_box_4pt(im, gt_box, (255, 0, 0))

        cv2.imwrite(os.path.join(TEST_RESULT, os.path.basename(t[0])), im)


if __name__ == '__main__':
    net = Net.CTPN()
    net.load_state_dict(torch.load('./model/bk_ctpn-mlt-5-end.model'))
    print(net)
    net.eval()

    if sys.argv[1] == 'random':
        random_test(net)
    else:
        url = sys.argv[1]
        infer_one(url, net)



