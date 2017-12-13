# adapted from http://www.pygame.org/wiki/OBJFileLoader

from algo import tools

#def MTL(filename):
#    contents = {}
#    mtl = None
#    for line in open(filename, "r"):
#        if line.startswith('#'): continue
#        values = line.split()
#        if not values: continue
#        if values[0] == 'newmtl':
#            mtl = contents[values[1]] = {}
#        elif mtl is None:
#            raise ValueError("mtl file doesn't start with newmtl stmt")
#        elif values[0] == 'map_Kd':
#            # load the texture referred to by this declaration
#            mtl[values[0]] = values[1]
#            surf = pygame.image.load(mtl['map_Kd'])
#            image = pygame.image.tostring(surf, 'RGBA', 1)
#            ix, iy = surf.get_rect().size
#            texid = mtl['texture_Kd'] = glGenTextures(1)
#            glBindTexture(GL_TEXTURE_2D, texid)
#            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER,
#                GL_LINEAR)
#            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER,
#                GL_LINEAR)
#            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, ix, iy, 0, GL_RGBA,
#                GL_UNSIGNED_BYTE, image)
#        else:
#            mtl[values[0]] = map(float, values[1:])
#    return contents
 
class ShapeModel:
    def __init__(self, fname=None, data=None):
        self.vertices = []
        self.faces = []
        
        if fname is not None:
            self.from_file(fname)
        elif data is not None:
            self.from_dict(data)
    
    def from_file(self, fname, swapyz=False):
        """Loads a Wavefront OBJ file. """
        self.vertices = []
        #self.normals = []
        #self.texcoords = []
        self.faces = []
        #self.triangles = []
 
        #material = None
        for line in open(fname, "r"):
            if line.startswith('#'): continue
            values = line.split()
            if not values: continue
            if values[0] == 'v':
                v = list(map(float, values[1:4]))
                if swapyz:
                    v = v[0], v[2], v[1]
                self.vertices.append(v)
            elif values[0] == 'vn':
                pass
#                v = list(map(float, values[1:4]))
#                if swapyz:
#                    v = v[0], v[2], v[1]
#                self.normals.append(v)
            elif values[0] == 'vt':
                pass
#                self.texcoords.append(map(float, values[1:3]))
            elif values[0] in ('usemtl', 'usemat'):
                pass
#                material = values[1]
            elif values[0] == 'mtllib':
                pass
#                self.mtl = MTL(values[1])
            elif values[0] == 'f':
                face = []
#                texcoords = []
#                norm = []
                for v in values[1:]:
                    w = v.split('/')
                    face.append(int(w[0])-1)
#                    if len(w) >= 2 and len(w[1]) > 0:
#                        texcoords.append(int(w[1]))
#                    else:
#                        texcoords.append(0)
#                    if len(w) >= 3 and len(w[2]) > 0:
#                        norm.append(int(w[2]))
#                    else:
#                        norm.append(0)
                    #self.faces.append((face, norms, texcoords, material))
                if len(face)==3:
                    self.faces.append((face, self._calc_norm(face)))
#                    self.triangles.append(tuple(face))
                else:
                    raise Exception('Not a triangle!')
    
    def from_dict(self, data):
        self.faces = data['faces']
        self.vertices = data['vertices']
        
    def as_dict(self):
        return {'faces':self.faces, 'vertices':self.vertices}
        
    def _calc_norm(self, face):
        return tools.surf_normal(
                self.vertices[face[0]],
                self.vertices[face[1]],
                self.vertices[face[2]])
    
    def recalc_norms(self):
        self.faces = [(face, self._calc_norm(face)) for face, n in self.faces]