import math
import os

import numpy as np
import quaternion

import moderngl
from ModernGL.ext.obj import Obj

from algo import tools
from algo.image import ImageProc
from iotools.objloader import ShapeModel
from missions.didymos import DidymosSystemModel, DidymosPrimary
from missions.rosetta import RosettaSystemModel, ChuryumovGerasimenko


class RenderEngine:
    _ctx = None

    (
        _LOC_TEXTURE,
        _LOC_SHADOW_MAP,
        _LOC_HAPKE_K,
    ) = range(3)

    (
        REFLMOD_LAMBERT,
        REFLMOD_LUNAR_LAMBERT,
        REFLMOD_HAPKE,
    ) = range(3)

    REFLMOD_PARAMS = {
        REFLMOD_LAMBERT: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        REFLMOD_LUNAR_LAMBERT: ChuryumovGerasimenko.LUNAR_LAMBERT_PARAMS,
        REFLMOD_HAPKE: ChuryumovGerasimenko.HAPKE_PARAMS,
    }

    # phase angle (g) range: np.linspace(0, 180, 19)
    # roughness angle range (th_p) range: np.linspace(0, 60, 7)
    HAPKE_K = np.array([
        [1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00],
#        [1.00, 0.997, 0.991, 0.984, 0.974, 0.961, 0.943],  # g=2deg
#        [1.00, 0.994, 0.981, 0.965, 0.944, 0.918, 0.881],  # g=5deg
        [1.00, 0.991, 0.970, 0.943, 0.909, 0.866, 0.809],
        [1.00, 0.988, 0.957, 0.914, 0.861, 0.797, 0.715],
        [1.00, 0.986, 0.947, 0.892, 0.825, 0.744, 0.644],
        [1.00, 0.984, 0.938, 0.871, 0.789, 0.692, 0.577],
        [1.00, 0.982, 0.926, 0.846, 0.748, 0.635, 0.509],
        [1.00, 0.979, 0.911, 0.814, 0.698, 0.570, 0.438],
        [1.00, 0.974, 0.891, 0.772, 0.637, 0.499, 0.366],
        [1.00, 0.968, 0.864, 0.719, 0.566, 0.423, 0.296],
        [1.00, 0.959, 0.827, 0.654, 0.487, 0.346, 0.231],
        [1.00, 0.946, 0.777, 0.575, 0.403, 0.273, 0.175],
        [1.00, 0.926, 0.708, 0.484, 0.320, 0.208, 0.130],
        [1.00, 0.894, 0.617, 0.386, 0.243, 0.153, 0.094],
        [1.00, 0.840, 0.503, 0.290, 0.175, 0.107, 0.064],
        [1.00, 0.747, 0.374, 0.201, 0.117, 0.070, 0.041],
        [1.00, 0.590, 0.244, 0.123, 0.069, 0.040, 0.023],
        [1.00, 0.366, 0.127, 0.060, 0.032, 0.018, 0.010],
        [1.00, 0.128, 0.037, 0.016, 0.0085, 0.0047, 0.0026],
        [1.00, 0, 0, 0, 0, 0, 0],
    ]).T


    def __init__(self, view_width, view_height, antialias_samples=0):
        antialias_samples=4
        if RenderEngine._ctx is None:
            RenderEngine._ctx = moderngl.create_standalone_context()

        self._ctx = RenderEngine._ctx
        self._width = view_width
        self._height = view_height
        self._samples = antialias_samples

        self._wireframe_prog = self._load_prog('wireframe.vert', 'wireframe.frag', 'wireframe.geom')
        self._shadow_prog = self._load_prog('shadow.vert', 'shadow.frag')
        self._prog = self._load_prog('shader_v400.vert', 'shader_v400.frag')
        self._prog['brightness_coef'].value = 0.65

        self._cbo = self._ctx.renderbuffer((view_width, view_height), samples=antialias_samples)
        self._dbo = self._ctx.depth_texture((view_width, view_height), samples=antialias_samples, alignment=1)
        self._fbo = self._ctx.framebuffer(self._cbo, self._dbo)

        if self._samples>0:
            self._cbo2 = self._ctx.renderbuffer((view_width, view_height))
            self._dbo2 = self._ctx.depth_texture((view_width, view_height), alignment=1)
            self._fbo2 = self._ctx.framebuffer(self._cbo2, self._dbo2)

        self._objs = []
        self._s_objs = []
        self._w_objs = []
        self._raw_objs = []
        self._textures = []
        self._persp_mx = None
        self._view_mx = np.identity(4)
        self._model_mx = None
        self._frustum_near = None
        self._frustum_far = None

    def _load_prog(self, vert, frag, geom=None):
        vertex_shader_source = open(os.path.join(os.path.dirname(__file__), vert)).read()
        fragment_shader_source = open(os.path.join(os.path.dirname(__file__), frag)).read()
        geom_shader_source = None if geom is None else open(os.path.join(os.path.dirname(__file__), geom)).read()
        return self._ctx.program(vertex_shader=vertex_shader_source,
                                 fragment_shader=fragment_shader_source,
                                 geometry_shader=geom_shader_source)

    @property
    def ctx(self):
        return self._ctx

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    def set_frustum(self, x_fov, y_fov, frustum_near, frustum_far):
        self._frustum_near = frustum_near
        self._frustum_far = frustum_far

        # calculate projection matrix based on frustum
        n = frustum_near
        f = frustum_far
        r = n * math.tan(math.radians(x_fov/2))
        t = n * math.tan(math.radians(y_fov/2))

        self._persp_mx = np.zeros((4, 4))
        self._persp_mx[0, 0] = n/r
        self._persp_mx[1, 1] = n/t
        self._persp_mx[2, 2] = -(f+n)/(f-n)
        self._persp_mx[3, 2] = -1
        self._persp_mx[2, 3] = -2*f*n/(f-n)

    def load_object(self, object, obj_idx=None, smooth=False, wireframe=False):
        vertex_data = None
        if isinstance(object, str):
            object = ShapeModel(fname=object)
        elif isinstance(object, Obj):
            vertex_data = object
            assert not smooth, 'not supported'

        if isinstance(object, ShapeModel):
            if smooth:
                verts, tex, norms, faces = object.export_smooth_faces()
            else:
                verts, tex, norms, faces = object.export_angular_faces()

            vertex_data = Obj(verts, tex, norms, faces)
            texture_data = object.load_texture()

        assert vertex_data is not None, 'wrong object type'

        if wireframe:
            w_vbo = self._ctx.buffer(vertex_data.pack('vx vy vz'))
            w_obj = self._ctx.simple_vertex_array(self._wireframe_prog, w_vbo, 'vertexPosition_modelFrame')
        else:
            texture = None
            if texture_data is not None:
                texture = self._ctx.texture(texture_data.T.shape, 1, np.flipud(texture_data).tobytes())
                texture.build_mipmaps()

            vbo = self._ctx.buffer(vertex_data.pack('vx vy vz nx ny nz tx ty'))
            obj = self._ctx.simple_vertex_array(self._prog, vbo, 'vertexPosition_modelFrame', 'vertexNormal_modelFrame', 'aTexCoords')

            s_vbo = self._ctx.buffer(vertex_data.pack('vx vy vz'))
            s_obj = self._ctx.simple_vertex_array(self._shadow_prog, s_vbo, 'vertexPosition_modelFrame')

        if obj_idx is None:
            if wireframe:
                self._w_objs.append(w_obj)
            else:
                self._objs.append(obj)
                self._s_objs.append(s_obj)
                self._raw_objs.append(vertex_data)
                self._textures.append(texture)
        else:
            if wireframe:
                self._w_objs[obj_idx] = w_obj
            else:
                self._objs[obj_idx] = obj
                self._s_objs[obj_idx] = s_obj
                self._raw_objs[obj_idx] = vertex_data
                self._textures[obj_idx] = texture

        return len(self._w_objs if wireframe else self._objs)-1

    def render_wireframe(self, obj_idxs, rel_pos_v, rel_rot_q, color):
        obj_idxs = [obj_idxs] if isinstance(obj_idxs, int) else obj_idxs
        rel_pos_v = np.array(rel_pos_v).reshape((-1, 3))
        rel_rot_q = np.array(rel_rot_q).reshape((-1, 1))
        color = np.array(color).reshape((-1, 3))
        assert len(obj_idxs) == rel_pos_v.shape[0] == rel_rot_q.shape[0], 'obj_idxs, rel_pos_v and rel_rot_q dimensions dont match'

        self._fbo.use()
        self._ctx.disable(moderngl.DEPTH_TEST)
        self._ctx.disable(moderngl.CULL_FACE)
        #self._ctx.front_face = 'ccw'  # cull back faces (front faces suggested but that had glitches)
        self._ctx.clear(0, 0, 0, float('inf'))

        # self._ctx.clear(depth=float('inf'))
        for i, obj_idx in enumerate(obj_idxs):
            self._set_params(obj_idx, rel_pos_v[i], rel_rot_q[i], for_wireframe=True)
            self._wireframe_prog['color'].value = tuple(color[i])
            self._w_objs[obj_idx].render()

        if self._samples > 0:
            self._ctx.copy_framebuffer(self._fbo2, self._fbo)
            fbo = self._fbo2
        else:
            fbo = self._fbo

        data = np.frombuffer(fbo.read(components=3, alignment=1), dtype='u1').reshape((self._height, self._width, 3))
        data = np.flipud(data)

        return data

    def render(self, obj_idxs, rel_pos_v, rel_rot_q, light_v, get_depth=False, shadows=True, textures=True,
               gamma=1.0, reflection=REFLMOD_LUNAR_LAMBERT):

        obj_idxs = [obj_idxs] if isinstance(obj_idxs, int) else obj_idxs
        rel_pos_v = np.array(rel_pos_v).reshape((-1, 3))
        rel_rot_q = np.array(rel_rot_q).reshape((-1,))
        light_v = np.array(light_v)
        assert len(obj_idxs) == rel_pos_v.shape[0] == rel_rot_q.shape[0], 'obj_idxs, rel_pos_v and rel_rot_q dimensions dont match'

        if shadows:
            self._render_shadowmap(obj_idxs, rel_rot_q, light_v)

        self._fbo.use()
        self._ctx.enable(moderngl.DEPTH_TEST)
        self._ctx.enable(moderngl.CULL_FACE)
        self._ctx.front_face = 'ccw'  # cull back faces
        self._ctx.clear(0, 0, 0, float('inf'))
        if shadows:
            self._shadow_map.use(RenderEngine._LOC_SHADOW_MAP)
            self._prog['shadow_map'].value = RenderEngine._LOC_SHADOW_MAP

        for i, obj_idx in enumerate(obj_idxs):
            self._set_params(obj_idx, rel_pos_v[i], rel_rot_q[i], light_v, shadows, textures, reflection)
            self._objs[obj_idx].render()

        if self._samples > 0:
            self._ctx.copy_framebuffer(self._fbo2, self._fbo)
            fbo = self._fbo2
            dbo = self._dbo2
        else:
            fbo = self._fbo
            dbo = self._dbo

        data = np.frombuffer(fbo.read(components=3, alignment=1), dtype='u1').reshape((self._height, self._width, 3))
        data = np.flipud(data)

        if get_depth:
            a = -(self._frustum_far - self._frustum_near) / (2.0 * self._frustum_far * self._frustum_near)
            b = (self._frustum_far + self._frustum_near) / (2.0 * self._frustum_far * self._frustum_near)
            depth = np.frombuffer(dbo.read(alignment=1), dtype='f4').reshape((self._height, self._width))
            depth = np.divide(1.0, (2.0 * a) * depth - (a - b))  # 1/((2*X-1)*a+b)
            depth = np.flipud(depth)

        if gamma != 1.0:
            data = ImageProc.adjust_gamma(data, gamma)

        return (data, depth) if get_depth else data

    def _set_params(self, obj_idx, rel_pos_v, rel_rot_q, light_v=None, use_shadows=True, use_textures=True,
                    reflection=REFLMOD_LUNAR_LAMBERT, for_wireframe=False):

        self._model_mx = np.identity(4)
        self._model_mx[:3, :3] = quaternion.as_rotation_matrix(rel_rot_q)
        self._model_mx[:3, 3] = rel_pos_v

        prog = self._wireframe_prog if for_wireframe else self._prog
        mv = self._view_mx.dot(self._model_mx)
        mvp = self._persp_mx.dot(mv)
        prog['mvp'].write((mvp.T).astype('float32').tobytes())

        if not for_wireframe:
            prog['mv'].write((mv.T).astype('float32').tobytes())
            use_texture = use_textures and self._textures[obj_idx] is not None
            prog['use_texture'].value = use_texture
            if use_texture:
                self._textures[obj_idx].use(RenderEngine._LOC_TEXTURE)
                prog['texture_map'].value = RenderEngine._LOC_TEXTURE

            prog['lightDirection_viewFrame'].value = tuple(-light_v)  # already in view frame
            prog['reflection_model'].value = reflection
            prog['model_coefs'].value = RenderEngine.REFLMOD_PARAMS[reflection]
            prog['use_shadows'].value = use_shadows
            if reflection == RenderEngine.REFLMOD_HAPKE and RenderEngine.REFLMOD_PARAMS[reflection][9] % 2 > 0:
                hapke_K = self._ctx.texture((7, 19), 1, data=RenderEngine.HAPKE_K.T.astype('float32').tobytes(), alignment=1, dtype='f4')
                hapke_K.use(RenderEngine._LOC_HAPKE_K)
                prog['hapke_K'].value = RenderEngine._LOC_HAPKE_K


    def _render_shadowmap(self, obj_idxs, rel_rot_q, light_v):
        # shadows following http://www.opengl-tutorial.org/intermediate-tutorials/tutorial-16-shadow-mapping/

        v = np.identity(4)
        angle = math.acos(np.clip(np.array([0, 0, -1]).dot(light_v), -1, 1))
        axis = np.cross(np.array([0, 0, -1]), light_v)
        q_cam2light = tools.angleaxis_to_q((angle, *axis))
        v[:3, :3] = quaternion.as_rotation_matrix(q_cam2light.conj())

        mvs = {}
        for i in obj_idxs:
            m = np.identity(4)
            m[:3, :3] = quaternion.as_rotation_matrix(rel_rot_q[i])
            mv = v.dot(m)
            mvs[i] = mv

        proj = self._ortho_mx(obj_idxs, mvs)

        self._fbo.use()
        self._ctx.enable(moderngl.DEPTH_TEST)
        self._ctx.enable(moderngl.CULL_FACE)
        self._ctx.front_face = 'ccw'  # cull back faces (front faces suggested but that had glitches)

        self._ctx.clear(depth=float('inf'))
        for i in obj_idxs:
            mvp = proj.dot(mvs[i])
            self._shadow_prog['mvp'].write(mvp.T.astype('float32').tobytes())
            self._s_objs[i].render()

        if self._samples > 0:
            self._ctx.copy_framebuffer(self._fbo2, self._fbo)
            dbo = self._dbo2
        else:
            dbo = self._dbo

        data = dbo.read(alignment=1)
        self._shadow_map = self._ctx.texture((self._width, self._height), 1, data=data, alignment=1, dtype='f4')

        b = self._bias_mx()
        shadow_mvp = b.dot(mvp)
        self._prog['shadow_mvp'].write(shadow_mvp.T.astype('float32').tobytes())
        self._prog['use_shadows'].value = True

        if False:
            import cv2
            d = np.frombuffer(data, dtype='f4').reshape((self._width, self._height))
            a = np.max(d.flatten())
            b = np.min(d.flatten())
            print('%s,%s' % (a, b))
            cv2.imshow('distance from sun', d)
            #cv2.waitKey()
            #quit()

    def _ortho_mx(self, obj_idxs, mvs):
        l = float('inf') # min x
        r = -float('inf') # max x
        b = float('inf') # min y
        t = -float('inf') # max y
        n = float('inf') # min z
        f = -float('inf') # max z
        for i in obj_idxs:
            v3d = np.array(self._raw_objs[i].vert)
            vert = mvs[i].dot(np.concatenate((v3d, np.ones((len(v3d),1))), axis=1).T).T
            vert = vert[:,:3] / vert[:,3:]
            x0, y0, z0 = np.min(vert, axis=0)
            x1, y1, z1 = np.max(vert, axis=0)
            l = min(l, x0)
            r = max(r, x1)
            b = min(b, y0)
            t = max(t, y1)
            n = min(n, z0)
            f = max(f, z1)

        P = np.identity(4)
        P[0, 0] = 2 / (r - l)
        P[1, 1] = 2 / (t - b)
        P[2, 2] = -2 / (f - n)
        P[0, 3] = -(r + l) / (r - l)
        P[1, 3] = -(t + b) / (t - b)
        P[2, 3] = (f + n) / (f - n)

        if False:
            # transform should result that all are in range [-1,1]
            tr = P.dot(np.array([
                [l, b, n, 1],
                [r, t, f, 1],
            ]).T)
            print('%s'%tr)

        return P

    def _bias_mx(self):
        return np.array([
            [0.5, 0.0, 0.0, 0.5],
            [0.0, 0.5, 0.0, 0.5],
            [0.0, 0.0, 0.5, 0.5],
            [0.0, 0.0, 0.0, 1.0],
        ])


if __name__ == '__main__':
    from settings import *
    import cv2
    sm = DidymosSystemModel(use_narrow_cam=False)
#    sm = RosettaSystemModel()
    re = RenderEngine(sm.cam.width//2, sm.cam.height//2)
    re.set_frustum(sm.cam.x_fov, sm.cam.y_fov, sm.min_altitude*0.5, sm.max_distance)
    pos = [0, 0, -sm.min_med_distance * 1]
    q = tools.angleaxis_to_q((math.radians(36), 0, 1, 0))

    #obj_idx = re.load_object('../data/67p-17k.obj')
    #obj_idx = re.load_object('../data/67p-4k.obj')
    #obj_idx = re.load_object('../data/ryugu+tex-d1-4k.obj')
    if False:
        obj_idx = re.load_object(os.path.join(BASE_DIR, 'data/ryugu+tex-d1-100.obj'), wireframe=True)
        q = tools.angleaxis_to_q((math.radians(3), 0, 1, 0))
        pos = [0, 0, -4]
        for i in range(60):
            image = re.render_wireframe(obj_idx, pos, q ** i, (0, 1, 0))
            cv2.imshow('fs', image)
            cv2.waitKey()
        quit()
    else:
        #obj_idx = re.load_object(sm.asteroid.target_model_file)
        obj_idx = re.load_object(sm.asteroid.hires_target_model_file)
    #obj_idx = re.load_object(sm.asteroid.target_model_file)
    #obj_idx = re.load_object(os.path.join(BASE_DIR, 'data/test-ball.obj'))


    if False:
        for i in range(36):
            image = re.render(obj_idx, [0, 0, -sm.min_med_distance*3], q**i, np.array([1, 0, 0])/math.sqrt(1), get_depth=False)
            cv2.imshow('image', image)
            cv2.waitKey()

    elif True:
        RenderEngine.REFLMOD_PARAMS[RenderEngine.REFLMOD_HAPKE] = DidymosPrimary.HAPKE_PARAMS
        RenderEngine.REFLMOD_PARAMS[RenderEngine.REFLMOD_LUNAR_LAMBERT] = DidymosPrimary.LUNAR_LAMBERT_PARAMS
        imgs = ()
        i = 1
        th = math.radians(100)
        #for i in range(4, 7):
        for th in np.linspace(math.radians(90), 0, 4):
            imgs_j = ()
            for j, hapke in enumerate((True, False)):
                model = RenderEngine.REFLMOD_HAPKE if hapke else RenderEngine.REFLMOD_LUNAR_LAMBERT
                if hapke and j == 0:
                    RenderEngine.REFLMOD_PARAMS[model][9] = 0
                if hapke and j == 1:
                    RenderEngine.REFLMOD_PARAMS[model][9] = 1
                light = tools.q_times_v(tools.ypr_to_q(th, 0, 0), np.array([0, 0, -1]))
                image = re.render(obj_idx, pos, q**i, tools.normalize_v(light), get_depth=False, reflection=model)
                image = ImageProc.adjust_gamma(image, 1.8)
                imgs_j += (image,)
            imgs += (np.vstack(imgs_j),)

        #cv2.imshow('depth', np.clip((sm.min_med_distance+sm.asteroid.mean_radius - depth)/5, 0, 1))
        cv2.imshow('images', np.hstack(imgs))
        cv2.waitKey()
