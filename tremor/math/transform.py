import numpy as np
from scipy.spatial.transform import Rotation

from tremor.math import matrix


# A transform is a translation, rotation, and scale
class Transform:
    def __init__(self, scene_elem):
        self._translation = np.array([0, 0, 0], dtype='float32')  # x y z
        self._rotation = np.array([0, 0, 0, 1], dtype='float32')  # w z y x
        self._scale = np.array([1, 1, 1])  # x y z
        self._mv_needs_rebuild = True
        self._mv: np.ndarray = None
        self._elem = scene_elem

    def to_model_view_matrix(self):
        # cache mv matrix
        if self._mv_needs_rebuild:
            self._mv = self._get_translation_matrix().dot(  # apply translation
                self._get_rotation_matrix().dot(  # apply rotation
                    self._get_scale_matrix()  # apply scaling
                ))
            self._mv_needs_rebuild = False
        return self._mv

    def to_model_view_matrix_global(self):
        # non-recursive, could probably be
        hierarchy = [self._elem]
        ce = self._elem
        while ce.parent is not None:
            hierarchy.insert(0, ce.parent)
            ce = ce.parent
        mvmat = np.identity(4, dtype='float32')
        for elem in hierarchy:
            mvmat = mvmat.dot(elem.transform.to_model_view_matrix())
        return mvmat

    def _get_rotation_matrix(self):
        rot = np.zeros((4, 4), dtype='float32')

        rot[:3, :3] = Rotation.from_quat(self._rotation).as_matrix()
        rot[3, 3] = 1
        return rot

    def _get_translation_matrix(self):
        trans_mat = matrix.create_translation_matrix(self._translation)
        return trans_mat

    def _get_scale_matrix(self):
        return matrix.create_scale_matrix(*self._scale)

    def set_translation(self, trans_vec: np.ndarray):
        if not len(trans_vec) == 3:
            raise Exception("Invalid translation vector!")
        self._mv_needs_rebuild = True
        self._translation = trans_vec

    def set_rotation(self, rot_quat: np.ndarray):
        if not len(rot_quat) == 4:
            raise Exception("Invalid rotation quaternion!")
        self._mv_needs_rebuild = True
        self._rotation = rot_quat

    def set_scale(self, scale_vec: np.ndarray):
        if not len(scale_vec) == 3:
            raise Exception("Invalid scale vector!")
        self._mv_needs_rebuild = True
        self._scale = scale_vec

    def get_translation(self):
        return self._translation

    def get_rotation(self):
        return self._rotation

    def get_scale(self):
        return self._scale

    def translate_global(self, trans_vec: np.ndarray):
        if not len(trans_vec) == 3:
            raise Exception("Invalid translation vector!")
        self.set_translation(trans_vec + self._translation)

    def translate_local(self, trans_vec: np.ndarray):
        if not len(trans_vec) == 3:
            raise Exception("Invalid translation vector!")
        position_mat = self._get_translation_matrix().dot(
            self._get_rotation_matrix().dot(
                matrix.create_translation_matrix(trans_vec)
            )
        )
        self.set_translation(matrix.translation_from_matrix(position_mat))

    def rotate_local(self, rot_quat: np.ndarray):
        if not len(rot_quat) == 4:
            raise Exception("Invalid rotation quaternion!")
        position_mat = self._get_translation_matrix().dot(
            self._get_rotation_matrix().dot(
                matrix.create_rotation_matrix_from_quaternion(rot_quat)
            )
        )
        self.set_rotation(matrix.quaternion_from_matrix(position_mat))
