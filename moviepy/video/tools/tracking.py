"""
This module contains different fonctions for tracking objects in videos,
manually or automatically. The tracking functions return results under
the form:  ``( txy, (fx,fy) )`` where txy is of the form [(ti, xi, yi)...]
and (fx(t),fy(t)) give the position of the track for all times t (if the
time t is out of the time bounds of the tracking time interval
fx and fy return the position of the object at the start or at the end
of the tracking time interval).
"""

from scipy.interpolate import interp1d

from ..io.preview import imdisplay
from .interpolators import Trajectory
from moviepy.decorators import time_can_be_tuple


try:
    import cv2
    autotracking_possible = True
except:
    # Note: this will be later fixed with scipy/skimage replacements
    # but for the moment OpenCV is mandatory, so...
    autotracking_possible = False


# WE START WITH A TOOL FUNCTION

# MANUAL TRACKING

@time_can_be_tuple
def manual_tracking(clip, t1=None, t2=None, fps=5, nobjects = 1,
                    savefile = None):
    """
    Allows manual tracking of an object(s) in the video clip between
    times `t1` and `t2`. This displays the clip frame by frame
    and you must click on the object(s) in each frame. If ``t2=None``
    only the frame at ``t1`` is taken into account.
    
    Returns a list [(t1,x1,y1),(t2,x2,y2) etc... ] if there is one
    object per frame, else returns a list whose elements are of the 
    form (ti, [(xi1,yi1), (xi2,yi2), ...] )
    
    :param t1,t2: times during which to track (defaults are start and
        end of the clip)
    :param fps: Number of frames per second to freeze on.
    :param nobjects: Number of objects to click on each frame
    

    
    >>> print myClip.manTrack(10, 13,fps=7)
    >>>
    >>> # To print 5 points coordinates at t=5 : 
    >>> for i in range(5):
    >>>     print myClip.manTrack(5)
    
    Tip: To avoid redoing the tracking each time you run your script,
    better save the result the first time and then load it at each run. 
    
    >>> # First time:
    >>> import pickle
    >>> txy = myClip.manTrack(20, 10,fps=10)
    >>> with open("chaplin_txy.dat",'w+') as f:
    >>>     pickle.dump(txy,f)
    >>>
    >>> # Next times:
    >>> import pickle
    >>> with open("chaplin_txy.dat",'r') as f:
    >>>     txy = pickle.load(txy,f)
    
    """
    
    import pygame as pg
    
    screen = pg.display.set_mode(clip.size)
    step = 1.0 / fps
    if (t1 is None) and (t2 is None):
        t1,t2 = 0, clip.duration
    elif (t2 is None):
        t2 = t1 + step / 2
    t = t1
    txy_list = []
    
    def gatherClicks(t):
        
        imdisplay(clip.get_frame(t), screen)
        objects_to_click = nobjects
        clicks = []
        while objects_to_click:

            for event in pg.event.get():

                if event.type == pg.KEYDOWN:
                    if (event.key == pg.K_BACKSLASH):
                        return "return"
                    elif (event.key == pg.K_ESCAPE):
                        raise KeyboardInterrupt()
                        

                elif event.type == pg.MOUSEBUTTONDOWN:
                    x, y = pg.mouse.get_pos()
                    clicks.append((x, y))
                    objects_to_click -= 1
                    
        return clicks
        
    while t < t2:
        
        clicks  =gatherClicks(t)
        if clicks == 'return':
            txy_list.pop()
            t -= step
        else:
            txy_list.append((t,clicks))
            t += step

    tt, xylist = zip(*txy_list) 
    result = []
    for i in range(nobjects):
        xys = [e[i] for e in xylist]
        xx, yy = zip(*xys)
        result.append(Trajectory(tt, xx, yy))
    
    if savefile is not None:
        Trajectory.save_list(result, savefile)
    return result


# AUTOMATED TRACKING OF A PATTERN

def findAround(pic,pat,xy=None,r=None):
    """
    find image pattern ``pat`` in ``pic[x +/- r, y +/- r]``.
    if xy is none, consider the whole picture.
    """
    
    if xy and r:
        h,w = pat.shape[:2]
        x,y = xy
        pic = pic[y-r : y+h+r , x-r : x+w+r]
        
    matches = cv2.matchTemplate(pat,pic,cv2.TM_CCOEFF_NORMED)
    yf,xf = np.unravel_index(matches.argmax(),matches.shape)
    return (x-r+xf,y-r+yf) if (xy and r) else (xf,yf)
        
        
def autoTrack(clip, pattern, tt=None, fps=None, radius=20, xy0=None):
    """
    Tracks a given pattern (small image array) in a video clip.
    Returns [(x1,y1),(x2,y2)...] where xi,yi are
    the coordinates of the pattern in the clip on frame i.
    To select the frames you can either specify a list of times with ``tt``
    or select a frame rate with ``fps``.
    This algorithm assumes that the pattern's aspect does not vary much
    and that the distance between two occurences of the pattern in
    two consecutive frames is smaller than ``radius`` (if you set ``radius``
    to -1 the pattern will be searched in the whole screen at each frame).
    You can also provide the original position of the pattern with xy0.
    """

    if not autotracking_possible:
        raise IOError("Sorry, autotrack requires OpenCV for the moment. "
                      "Install OpenCV (aka cv2) to use it.")


    if not xy0:
        xy0 = findAround(clip.get_frame(tt[0]),pattern)
    
    if tt is None:
        tt = np.arange(0, clip.duration, 1.0/fps)
        
    xys = [xy0]
    for t in tt[1:]:
        xys.append( findAround(clip.get_frame(t),pattern,
                               xy=xys[-1],r=radius))
    
    xx,yy = zip(*xys)

    return Trajectory(tt, xx, yy)
