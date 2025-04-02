"""Fabex 'bas_relief.py'

Module to allow the creation of reliefs from Images or View Layers.
(https://en.wikipedia.org/wiki/Relief#Bas-relief_or_low_relief)
"""

from math import ceil, floor, sqrt
import re
import time

import numpy

import bpy

from .constants import EPS, NUMPYALG
from .utilities.image_utils import (
    image_to_numpy,
    numpy_to_image,
)


class ReliefError(Exception):
    pass


def copy_compbuf_data(inbuf, outbuf):
    outbuf[:] = inbuf[:]


def restrict_buffer(inbuf, outbuf):
    """Restrict the resolution of an input buffer to match an output buffer.

    This function scales down the input buffer `inbuf` to fit the dimensions
    of the output buffer `outbuf`. It computes the average of the
    neighboring pixels in the input buffer to create a downsampled version
    in the output buffer. The method used for downsampling can vary based on
    the dimensions of the input and output buffers, utilizing either a
    simple averaging method or a more complex numpy-based approach.

    Args:
        inbuf (numpy.ndarray): The input buffer to be downsampled, expected to be
            a 2D array.
        outbuf (numpy.ndarray): The output buffer where the downsampled result will
            be stored, also expected to be a 2D array.

    Returns:
        None: The function modifies `outbuf` in place.
    """
    # scale down array....

    inx = inbuf.shape[0]
    iny = inbuf.shape[1]

    outx = outbuf.shape[0]
    outy = outbuf.shape[1]

    dx = inx / outx
    dy = iny / outy

    filterSize = 0.5
    xfiltersize = dx * filterSize

    sy = dy / 2 - 0.5
    if dx == 2 and dy == 2:  # much simpler method
        outbuf[:] = (
            inbuf[::2, ::2] + inbuf[1::2, ::2] + inbuf[::2, 1::2] + inbuf[1::2, 1::2]
        ) / 4.0

    elif NUMPYALG:  # numpy method
        yrange = numpy.arange(0, outy)
        xrange = numpy.arange(0, outx)

        w = 0
        sx = dx / 2 - 0.5

        sxrange = xrange * dx + sx
        syrange = yrange * dy + sy

        sxstartrange = numpy.array(numpy.ceil(sxrange - xfiltersize), dtype=int)
        sxstartrange[sxstartrange < 0] = 0
        sxendrange = numpy.array(numpy.floor(sxrange + xfiltersize) + 1, dtype=int)
        sxendrange[sxendrange > inx] = inx

        systartrange = numpy.array(numpy.ceil(syrange - xfiltersize), dtype=int)
        systartrange[systartrange < 0] = 0
        syendrange = numpy.array(numpy.floor(syrange + xfiltersize) + 1, dtype=int)
        syendrange[syendrange > iny] = iny

        # 3 is the maximum value...?pff.
        indices = numpy.arange(outx * outy * 2 * 3).reshape((2, outx * outy, 3))

        r = sxendrange - sxstartrange

        indices[0] = sxstartrange.repeat(outy)
        indices[1] = systartrange.repeat(outx).reshape(outx, outy).swapaxes(0, 1).flatten()

        outbuf.fill(0)
        tempbuf = inbuf[indices[0], indices[1]]
        tempbuf += inbuf[indices[0] + 1, indices[1]]
        tempbuf += inbuf[indices[0], indices[1] + 1]
        tempbuf += inbuf[indices[0] + 1, indices[1] + 1]
        tempbuf /= 4.0
        outbuf[:] = tempbuf.reshape((outx, outy))

    else:  # old method
        for y in range(0, outy):
            sx = dx / 2 - 0.5
            for x in range(0, outx):
                pixVal = 0
                w = 0

                #
                for ix in range(
                    max(0, ceil(sx - dx * filterSize)),
                    min(floor(sx + dx * filterSize), inx - 1) + 1,
                ):
                    for iy in range(
                        max(0, ceil(sy - dx * filterSize)),
                        min(floor(sy + dx * filterSize), iny - 1) + 1,
                    ):
                        pixVal += inbuf[ix, iy]
                        w += 1
                outbuf[x, y] = pixVal / w

                sx += dx
            sy += dy


def prolongate(inbuf, outbuf):
    """Prolongate an input buffer to a larger output buffer.

    This function takes an input buffer and enlarges it to fit the
    dimensions of the output buffer. It uses different methods to achieve
    this based on the scaling factors derived from the input and output
    dimensions. The function can handle specific cases where the scaling
    factors are exactly 0.5, as well as a general case that applies a
    bilinear interpolation technique for resizing.

    Args:
        inbuf (numpy.ndarray): The input buffer to be enlarged, expected to be a 2D array.
        outbuf (numpy.ndarray): The output buffer where the enlarged data will be stored,
            expected to be a 2D array of larger dimensions than inbuf.
    """

    inx = inbuf.shape[0]
    iny = inbuf.shape[1]

    outx = outbuf.shape[0]
    outy = outbuf.shape[1]

    dx = inx / outx
    dy = iny / outy

    filterSize = 1
    xfiltersize = dx * filterSize

    if dx == 0.5 and dy == 0.5:
        outbuf[::2, ::2] = inbuf
        outbuf[1::2, ::2] = inbuf
        outbuf[::2, 1::2] = inbuf
        outbuf[1::2, 1::2] = inbuf
    elif NUMPYALG:  # numpy method
        sy = -dy / 2
        sx = -dx / 2
        xrange = numpy.arange(0, outx)
        yrange = numpy.arange(0, outy)

        sxrange = xrange * dx + sx
        syrange = yrange * dy + sy

        sxstartrange = numpy.array(numpy.ceil(sxrange - xfiltersize), dtype=int)
        sxstartrange[sxstartrange < 0] = 0
        sxendrange = numpy.array(numpy.floor(sxrange + xfiltersize) + 1, dtype=int)
        sxendrange[sxendrange >= inx] = inx - 1
        systartrange = numpy.array(numpy.ceil(syrange - xfiltersize), dtype=int)
        systartrange[systartrange < 0] = 0
        syendrange = numpy.array(numpy.floor(syrange + xfiltersize) + 1, dtype=int)
        syendrange[syendrange >= iny] = iny - 1

        indices = numpy.arange(outx * outy * 2).reshape((2, outx * outy))
        indices[0] = sxstartrange.repeat(outy)
        indices[1] = systartrange.repeat(outx).reshape(outx, outy).swapaxes(0, 1).flatten()

        tempbuf = inbuf[indices[0], indices[1]]
        tempbuf /= 4.0
        outbuf[:] = tempbuf.reshape((outx, outy))

    else:
        sy = -dy / 2
        for y in range(0, outy):
            sx = -dx / 2
            for x in range(0, outx):
                pixVal = 0
                weight = 0

                for ix in range(
                    max(0, ceil(sx - filterSize)), min(floor(sx + filterSize), inx - 1) + 1
                ):
                    for iy in range(
                        max(0, ceil(sy - filterSize)), min(floor(sy + filterSize), iny - 1) + 1
                    ):
                        fx = abs(sx - ix)
                        fy = abs(sy - iy)

                        fval = (1 - fx) * (1 - fy)

                        pixVal += inbuf[ix, iy] * fval
                        weight += fval
                outbuf[x, y] = pixVal / weight
                sx += dx
            sy += dy


def idx(r, c, cols):
    return r * cols + c + 1


def smooth(U, F, linbcgiterations, planar):
    """Smooth a matrix U using a filter F at a specified level.

    This function applies a smoothing operation on the input matrix U using
    the filter F. It utilizes the linear Biconjugate Gradient method for the
    smoothing process. The number of iterations for the linear BCG method is
    specified by linbcgiterations, and the planar parameter indicates
    whether the operation is to be performed in a planar manner.

    Args:
        U (numpy.ndarray): The input matrix to be smoothed.
        F (numpy.ndarray): The filter used for smoothing.
        linbcgiterations (int): The number of iterations for the linear BCG method.
        planar (bool): A flag indicating whether to perform the operation in a planar manner.

    Returns:
        None: This function modifies the input matrix U in place.
    """

    iter = 0
    err = 0

    rows = U.shape[1]
    cols = U.shape[0]

    n = U.size

    linear_bcg(n, F, U, 2, 0.001, linbcgiterations, iter, err, rows, cols, planar)


def calculate_defect(D, U, F):
    """Calculate the defect of a grid based on the input fields.

    This function computes the defect values for a grid by comparing the
    input field `F` with the values in the grid `U`. The defect is
    calculated using finite difference approximations, taking into account
    the neighboring values in the grid. The results are stored in the output
    array `D`, which is modified in place.

    Args:
        D (ndarray): A 2D array where the defect values will be stored.
        U (ndarray): A 2D array representing the current state of the grid.
        F (ndarray): A 2D array representing the target field to compare against.

    Returns:
        None: The function modifies the array `D` in place and does not return a
            value.
    """

    sx = F.shape[0]
    sy = F.shape[1]

    h = 1.0 / sqrt(sx * sy * 1.0)
    h2i = 1.0 / (h * h)

    h2i = 1
    D[1:-1, 1:-1] = (
        F[1:-1, 1:-1] - U[:-2, 1:-1] - U[2:, 1:-1] - U[1:-1, :-2] - U[1:-1, 2:] + 4 * U[1:-1, 1:-1]
    )
    # sides
    D[1:-1, 0] = F[1:-1, 0] - U[:-2, 0] - U[2:, 0] - U[1:-1, 1] + 3 * U[1:-1, 0]
    D[1:-1, -1] = F[1:-1, -1] - U[:-2, -1] - U[2:, -1] - U[1:-1, -2] + 3 * U[1:-1, -1]
    D[0, 1:-1] = F[0, 1:-1] - U[0, :-2] - U[0, :-2] - U[1, 1:-1] + 3 * U[0, 1:-1]
    D[-1, 1:-1] = F[-1, 1:-1] - U[-1, :-2] - U[-1, :-2] - U[-1, 1:-1] + 3 * U[-1, 1:-1]
    # corners
    D[0, 0] = F[0, 0] - U[0, 1] - U[1, 0] + 2 * U[0, 0]
    D[0, -1] = F[0, -1] - U[1, -1] - U[0, -2] + 2 * U[0, -1]
    D[-1, 0] = F[-1, 0] - U[-2, 0] - U[-1, 1] + 2 * U[-1, 0]
    D[-1, -1] = F[-1, -1] - U[-2, -1] - U[-1, -2] + 2 * U[-1, -1]


def add_correction(U, C):
    U += C


def solve_pde_multigrid(
    F, U, vcycleiterations, linbcgiterations, smoothiterations, mins, levels, useplanar, planar
):
    """Solve a partial differential equation using a multigrid method.

    This function implements a multigrid algorithm to solve a given partial
    differential equation (PDE). It operates on a grid of varying
    resolutions, applying smoothing and correction steps iteratively to
    converge towards the solution. The algorithm consists of several key
    phases: restriction of the right-hand side to coarser grids, solving on
    the coarsest grid, and then interpolating corrections back to finer
    grids. The process is repeated for a specified number of V-cycle
    iterations.

    Args:
        F (numpy.ndarray): The right-hand side of the PDE represented as a 2D array.
        U (numpy.ndarray): The initial guess for the solution, which will be updated in place.
        vcycleiterations (int): The number of V-cycle iterations to perform.
        linbcgiterations (int): The number of iterations for the linear solver used in smoothing.
        smoothiterations (int): The number of smoothing iterations to apply at each level.
        mins (int): Minimum grid size (not used in the current implementation).
        levels (int): The number of levels in the multigrid hierarchy.
        useplanar (bool): A flag indicating whether to use planar information during the solution
            process.
        planar (numpy.ndarray): A 2D array indicating planar information for the grid.

    Returns:
        None: The function modifies the input array U in place to contain the final
            solution.

    Note:
        The function assumes that the input arrays F and U have compatible
        shapes
        and that the planar array is appropriately defined for the problem
        context.
    """

    xmax = F.shape[0]
    ymax = F.shape[1]

    # int i  # index for simple loops
    # int k  # index for iterating through levels
    # int k2 # index for iterating through levels in V-cycles

    # 1. restrict f to coarse-grid (by the way count the number of levels)
    # k=0: fine-grid = f
    # k=levels: coarsest-grid
    # pix = CB_VAL#what is this>???
    # int cycle
    # int sx, sy

    RHS = []
    IU = []
    VF = []
    PLANAR = []
    for a in range(0, levels + 1):
        RHS.append(None)
        IU.append(None)
        VF.append(None)
        PLANAR.append(None)
    VF[0] = numpy.zeros((xmax, ymax), dtype=numpy.float64)
    # numpy.fill(pix)!? TODO

    RHS[0] = F.copy()
    IU[0] = U.copy()
    PLANAR[0] = planar.copy()

    sx = xmax
    sy = ymax
    # print(planar)
    for k in range(0, levels):
        # calculate size of next level
        sx = int(sx / 2)
        sy = int(sy / 2)
        PLANAR[k + 1] = numpy.zeros((sx, sy), dtype=numpy.float64)
        RHS[k + 1] = numpy.zeros((sx, sy), dtype=numpy.float64)
        IU[k + 1] = numpy.zeros((sx, sy), dtype=numpy.float64)
        VF[k + 1] = numpy.zeros((sx, sy), dtype=numpy.float64)

        # restrict from level k to level k+1 (coarser-grid)
        restrict_buffer(PLANAR[k], PLANAR[k + 1])
        PLANAR[k + 1] = PLANAR[k + 1] > 0
        # numpytoimage(PLANAR[k+1],'planar')
        # print(PLANAR[k+1])
        restrict_buffer(RHS[k], RHS[k + 1])
        # numpytoimage(RHS[k+1],'rhs')

    # 2. find exact sollution at the coarsest-grid (k=levels)
    # this was replaced to easify code. exact_sollution( RHS[levels], IU[levels] )
    IU[levels].fill(0.0)

    # 3. nested iterations

    for k in range(levels - 1, -1, -1):
        print("K:", str(k))

        # 4. interpolate sollution from last coarse-grid to finer-grid
        # interpolate from level k+1 to level k (finer-grid)
        prolongate(IU[k + 1], IU[k])
        # print('k',k)
        # 4.1. first target function is the equation target function
        # 	(following target functions are the defect)
        copy_compbuf_data(RHS[k], VF[k])

        # print('lanar ')

        # 5. V-cycle (twice repeated)

        for cycle in range(0, vcycleiterations):
            print("v-cycle iteration:", str(cycle))

            # 6. downward stroke of V
            for k2 in range(k, levels):
                # 7. pre-smoothing of initial sollution using target function
                #  zero for initial guess at smoothing
                #  (except for level k when iu contains prolongated result)
                if k2 != k:
                    IU[k2].fill(0.0)

                for i in range(0, smoothiterations):
                    smooth(IU[k2], VF[k2], linbcgiterations, PLANAR[k2])

                # 8. calculate defect at level
                #  d[k2] = Lh * ~u[k2] - f[k2]

                D = numpy.zeros_like(IU[k2])
                # if k2==0:
                # IU[k2][planar[k2]]=IU[k2].max()
                # print(IU[0])
                if useplanar and k2 == 0:
                    IU[k2][PLANAR[k2]] = IU[k2].min()
                # if k2==0 :

                # 	VF[k2][PLANAR[k2]]=0.0
                # 	print(IU[0])
                calculate_defect(D, IU[k2], VF[k2])

                # 9. restrict deffect as target function for next coarser-grid
                #  def -> f[k2+1]
                restrict_buffer(D, VF[k2 + 1])

            # 10. solve on coarsest-grid (target function is the deffect)
            #   iu[levels] should contain sollution for
            #   the f[levels] - last deffect, iu will now be the correction
            IU[levels].fill(0.0)  # exact_sollution(VF[levels], IU[levels] )

            # 11. upward stroke of V
            for k2 in range(levels - 1, k - 1, -1):
                print("k2: ", str(k2))
                # 12. interpolate correction from last coarser-grid to finer-grid
                #   iu[k2+1] -> cor
                C = numpy.zeros_like(IU[k2])
                prolongate(IU[k2 + 1], C)

                # 13. add interpolated correction to initial sollution at level k2
                add_correction(IU[k2], C)

                # 14. post-smoothing of current sollution using target function
                for i in range(0, smoothiterations):
                    smooth(IU[k2], VF[k2], linbcgiterations, PLANAR[k2])

                if useplanar and k2 == 0:
                    IU[0][planar] = IU[0].min()
                    # print(IU[0])

        # --- end of V-cycle

    # --- end of nested iteration

    # 15. final sollution
    #   IU[0] contains the final sollution

    U[:] = IU[0]


def asolve(b, x):
    x[:] = -4 * b


def atimes(x, res):
    """Apply a discrete Laplacian operator to a 2D array.

    This function computes the discrete Laplacian of a given 2D array `x`
    and stores the result in the `res` array. The Laplacian is calculated
    using finite difference methods, which involve summing the values of
    neighboring elements and applying specific boundary conditions for the
    edges and corners of the array.

    Args:
        x (numpy.ndarray): A 2D array representing the input values.
        res (numpy.ndarray): A 2D array where the result will be stored. It must have the same shape
            as `x`.

    Returns:
        None: The result is stored directly in the `res` array.
    """

    res[1:-1, 1:-1] = x[:-2, 1:-1] + x[2:, 1:-1] + x[1:-1, :-2] + x[1:-1, 2:] - 4 * x[1:-1, 1:-1]
    # sides
    res[1:-1, 0] = x[0:-2, 0] + x[2:, 0] + x[1:-1, 1] - 3 * x[1:-1, 0]
    res[1:-1, -1] = x[0:-2, -1] + x[2:, -1] + x[1:-1, -2] - 3 * x[1:-1, -1]
    res[0, 1:-1] = x[0, :-2] + x[0, 2:] + x[1, 1:-1] - 3 * x[0, 1:-1]
    res[-1, 1:-1] = x[-1, :-2] + x[-1, 2:] + x[-2, 1:-1] - 3 * x[-1, 1:-1]
    # corners
    res[0, 0] = x[1, 0] + x[0, 1] - 2 * x[0, 0]
    res[-1, 0] = x[-2, 0] + x[-1, 1] - 2 * x[-1, 0]
    res[0, -1] = x[0, -2] + x[1, -1] - 2 * x[0, -1]
    res[-1, -1] = x[-1, -2] + x[-2, -1] - 2 * x[-1, -1]


def snrm(n, sx, itol):
    """Calculate the square root of the sum of squares or the maximum absolute
    value.

    This function computes a value based on the input parameters. If the
    tolerance level (itol) is less than or equal to 3, it calculates the
    square root of the sum of squares of the input array (sx). If the
    tolerance level is greater than 3, it returns the maximum absolute value
    from the input array.

    Args:
        n (int): An integer parameter, though it is not used in the current
            implementation.
        sx (numpy.ndarray): A numpy array of numeric values.
        itol (int): An integer that determines which calculation to perform.

    Returns:
        float: The square root of the sum of squares if itol <= 3, otherwise the
            maximum absolute value.
    """

    if itol <= 3:
        temp = sx * sx
        ans = temp.sum()
        return sqrt(ans)
    else:
        temp = numpy.abs(sx)
        return temp.max()


def linear_bcg(n, b, x, itol, tol, itmax, iter, err, rows, cols, planar):
    """Solve a linear system using the Biconjugate Gradient Method.

    This function implements the Biconjugate Gradient Method as described in
    Numerical Recipes in C. It iteratively refines the solution to a linear
    system of equations defined by the matrix-vector product. The method is
    particularly useful for large, sparse systems where direct methods are
    inefficient. The function takes various parameters to control the
    iteration process and convergence criteria.

    Args:
        n (int): The size of the linear system.
        b (numpy.ndarray): The right-hand side vector of the linear system.
        x (numpy.ndarray): The initial guess for the solution vector.
        itol (int): The type of norm to use for convergence checks.
        tol (float): The tolerance for convergence.
        itmax (int): The maximum number of iterations allowed.
        iter (int): The current iteration count (should be initialized to 0).
        err (float): The error estimate (should be initialized).
        rows (int): The number of rows in the matrix.
        cols (int): The number of columns in the matrix.
        planar (bool): A flag indicating if the problem is planar.

    Returns:
        None: The solution is stored in the input array `x`.
    """

    p = numpy.zeros((cols, rows))
    pp = numpy.zeros((cols, rows))
    r = numpy.zeros((cols, rows))
    rr = numpy.zeros((cols, rows))
    z = numpy.zeros((cols, rows))
    zz = numpy.zeros((cols, rows))

    iter = 0
    atimes(x, r)
    r[:] = b - r
    rr[:] = r

    atimes(r, rr)  # minimum residual

    znrm = 1.0

    if itol == 1:
        bnrm = snrm(n, b, itol)

    elif itol == 2:
        asolve(b, z)
        bnrm = snrm(n, z, itol)

    elif itol == 3 or itol == 4:
        asolve(b, z)
        bnrm = snrm(n, z, itol)
        asolve(r, z)
        znrm = snrm(n, z, itol)
    else:
        print("illegal itol in linbcg")

    asolve(r, z)

    while iter <= itmax:
        iter += 1
        zm1nrm = znrm
        asolve(rr, zz)

        bknum = 0.0

        temp = z * rr

        bknum = temp.sum()  # -z[0]*rr[0]????

        if iter == 1:
            p[:] = z
            pp[:] = zz

        else:
            bk = bknum / bkden
            p = bk * p + z
            pp = bk * pp + zz
        bkden = bknum
        atimes(p, z)
        temp = z * pp
        akden = temp.sum()
        ak = bknum / akden
        atimes(pp, zz)

        x += ak * p
        r -= ak * z
        rr -= ak * zz

        asolve(r, z)

        if itol == 1 or itol == 2:
            znrm = 1.0
            err = snrm(n, r, itol) / bnrm
        elif itol == 3 or itol == 4:
            znrm = snrm(n, z, itol)
            if abs(zm1nrm - znrm) > EPS * znrm:
                dxnrm = abs(ak) * snrm(n, p, itol)
                err = znrm / abs(zm1nrm - znrm) * dxnrm
            else:
                err = znrm / bnrm
                continue
            xnrm = snrm(n, x, itol)

            if err <= 0.5 * xnrm:
                err /= xnrm
            else:
                err = znrm / bnrm
                continue
        if err <= tol:
            break


def tonemap(i, exponent):
    """Apply tone mapping to an image array.

    This function performs tone mapping on the input image array by first
    filtering out values that are excessively high, which may indicate that
    the depth buffer was not written correctly. It then normalizes the
    values between the minimum and maximum heights, and finally applies an
    exponentiation to adjust the brightness of the image.

    Args:
        i (numpy.ndarray): A numpy array representing the image data.
        exponent (float): The exponent used for adjusting the brightness
            of the normalized image.

    Returns:
        None: The function modifies the input array in place.
    """

    # if depth buffer never got written it gets set
    # to a great big value (10000000000.0)
    # filter out anything within an order of magnitude of it
    # so we only have things that are actually drawn
    maxheight = i.max(where=i < 1000000000.0, initial=0)
    minheight = i.min()
    i[:] = numpy.clip(i, minheight, maxheight)

    i[:] = ((i - minheight)) / (maxheight - minheight)
    i[:] **= exponent


def vert(column, row, z, XYscaling, Zscaling):
    """Create a single vertex in 3D space.

    This function calculates the 3D coordinates of a vertex based on the
    provided column and row values, as well as scaling factors for the X-Y
    and Z dimensions. The resulting coordinates are scaled accordingly to
    fit within a specified 3D space.

    Args:
        column (float): The column value representing the X coordinate.
        row (float): The row value representing the Y coordinate.
        z (float): The Z coordinate value.
        XYscaling (float): The scaling factor for the X and Y coordinates.
        Zscaling (float): The scaling factor for the Z coordinate.

    Returns:
        tuple: A tuple containing the scaled X, Y, and Z coordinates.
    """
    return column * XYscaling, row * XYscaling, z * Zscaling


def build_mesh(mesh_z, br):
    """Build a 3D mesh from a height map and apply transformations.

    This function constructs a 3D mesh based on the provided height map
    (mesh_z) and applies various transformations such as scaling and
    positioning based on the parameters defined in the br object. It first
    removes any existing BasReliefMesh objects from the scene, then creates
    a new mesh from the height data, and finally applies decimation if the
    specified ratio is within acceptable limits.

    Args:
        mesh_z (numpy.ndarray): A 2D array representing the height values
            for the mesh vertices.
        br (object): An object containing properties for width, height,
            thickness, justification, and decimation ratio.
    """

    global rows
    global size
    scale = 1
    scalez = 1
    decimateRatio = br.decimate_ratio  # get variable from interactive table
    bpy.ops.object.select_all(action="DESELECT")
    for object in bpy.data.objects:
        if re.search("BasReliefMesh", str(object)):
            bpy.data.objects.remove(object)
            print("old basrelief removed")

    print("Building Mesh")
    numY = mesh_z.shape[1]
    numX = mesh_z.shape[0]
    print(numX, numY)

    verts = list()
    faces = list()

    for i, row in enumerate(mesh_z):
        for j, col in enumerate(row):
            verts.append(vert(i, j, col, scale, scalez))

    count = 0
    for i in range(0, numY * (numX - 1)):
        if count < numY - 1:
            A = i  # the first vertex
            B = i + 1  # the second vertex
            C = (i + numY) + 1  # the third vertex
            D = i + numY  # the fourth vertex

            face = (A, B, C, D)
            faces.append(face)
            count = count + 1
        else:
            count = 0

    # Create Mesh Datablock
    mesh = bpy.data.meshes.new("displacement")
    mesh.from_pydata(verts, [], faces)

    mesh.update()

    # make object from mesh
    new_object = bpy.data.objects.new("BasReliefMesh", mesh)
    scene = bpy.context.scene
    scene.collection.objects.link(new_object)

    # mesh object is made - preparing to decimate.
    ob = bpy.data.objects["BasReliefMesh"]
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.context.active_object.dimensions = (
        br.width_mm / 1000,
        br.height_mm / 1000,
        br.thickness_mm / 1000,
    )
    bpy.context.active_object.location = (
        float(br.justify_x) * br.width_mm / 1000,
        float(br.justify_y) * br.height_mm / 1000,
        float(br.justify_z) * br.thickness_mm / 1000,
    )

    print("Faces:" + str(len(ob.data.polygons)))
    print("Vertices:" + str(len(ob.data.vertices)))
    if decimateRatio > 0.95:
        print("Skipping Decimate Ratio > 0.95")
    else:
        m = ob.modifiers.new(name="Foo", type="DECIMATE")
        m.ratio = decimateRatio
        print("Decimating with Ratio:" + str(decimateRatio))
        bpy.ops.object.modifier_apply(modifier=m.name)
        print("Decimated")
        print("Faces:" + str(len(ob.data.polygons)))
        print("Vertices:" + str(len(ob.data.vertices)))


# Switches to cycles render to CYCLES to render the sceen then switches it back to FABEX_RENDER for basRelief
def render_scene(width, height, bit_diameter, passes_per_radius, make_nodes, view_layer):
    """Render a scene using Blender's Cycles engine.

    This function switches the rendering engine to Cycles, sets up the
    necessary nodes for depth rendering if specified, and configures the
    render resolution based on the provided parameters. It ensures that the
    scene is in object mode before rendering and restores the original
    rendering engine after the process is complete.

    Args:
        width (int): The width of the render in pixels.
        height (int): The height of the render in pixels.
        bit_diameter (float): The diameter used to calculate the number of passes.
        passes_per_radius (int): The number of passes per radius for rendering.
        make_nodes (bool): A flag indicating whether to create render nodes.
        view_layer (str): The name of the view layer to be rendered.

    Returns:
        None: This function does not return any value.
    """

    print("Rendering Scene")
    scene = bpy.context.scene
    # make sure we're in object mode or else bad things happen
    if bpy.context.active_object:
        bpy.ops.object.mode_set(mode="OBJECT")

    scene.render.engine = "CYCLES"
    our_viewer = None
    our_renderer = None
    if make_nodes:
        # make depth render node and viewer node
        if scene.use_nodes == False:
            scene.use_nodes = True
        node_tree = scene.node_tree
        nodes = node_tree.nodes
        our_viewer = node_tree.nodes.new(type="CompositorNodeViewer")
        our_viewer.label = "CAM_basrelief_viewer"
        our_renderer = node_tree.nodes.new(type="CompositorNodeRLayers")
        our_renderer.label = "CAM_basrelief_renderlayers"
        our_renderer.layer = view_layer
        node_tree.links.new(
            our_renderer.outputs[our_renderer.outputs.find("Depth")],
            our_viewer.inputs[our_viewer.inputs.find("Image")],
        )
        scene.view_layers[view_layer].use_pass_z = True
        # set our viewer as active so that it is what gets rendered to viewer node image
        nodes.active = our_viewer

    # Set render resolution
    passes = bit_diameter / (2 * passes_per_radius)
    x = round(width / passes)
    y = round(height / passes)
    print(x, y, passes)
    scene.render.resolution_x = x
    scene.render.resolution_y = y
    scene.render.resolution_percentage = 100
    bpy.ops.render.render(animation=False, write_still=False, use_viewport=True, layer="", scene="")
    if our_renderer is not None:
        nodes.remove(our_renderer)
    if our_viewer is not None:
        nodes.remove(our_viewer)
    bpy.context.scene.render.engine = "FABEX_RENDER"
    print("Done Rendering")


def problem_areas(br):
    """Process image data to identify problem areas based on silhouette
    thresholds.

    This function analyzes an image and computes gradients to detect and
    recover silhouettes based on specified parameters. It utilizes various
    settings from the provided `br` object to adjust the processing,
    including silhouette thresholds, scaling factors, and iterations for
    smoothing and recovery. The function also handles image scaling and
    applies a gradient mask if specified. The resulting data is then
    converted back into an image format for further use.

    Args:
        br (object): An object containing various parameters for processing, including:
            - use_image_source (bool): Flag to determine if a specific image source
            should be used.
            - source_image_name (str): Name of the source image if
            `use_image_source` is True.
            - silhouette_threshold (float): Threshold for silhouette detection.
            - recover_silhouettes (bool): Flag to indicate if silhouettes should be
            recovered.
            - silhouette_scale (float): Scaling factor for silhouette recovery.
            - min_gridsize (int): Minimum grid size for processing.
            - smooth_iterations (int): Number of iterations for smoothing.
            - vcycle_iterations (int): Number of iterations for V-cycle processing.
            - linbcg_iterations (int): Number of iterations for linear BCG
            processing.
            - use_planar (bool): Flag to indicate if planar processing should be
            used.
            - gradient_scaling_mask_use (bool): Flag to indicate if a gradient
            scaling mask should be used.
            - gradient_scaling_mask_name (str): Name of the gradient scaling mask
            image.
            - depth_exponent (float): Exponent for depth adjustment.
            - silhouette_exponent (int): Exponent for silhouette recovery.
            - attenuation (float): Attenuation factor for processing.

    Returns:
        None: The function does not return a value but processes the image data and
            saves the result.
    """

    t = time.time()
    if br.use_image_source:
        i = bpy.data.images[br.source_image_name]
    else:
        i = bpy.data.images["Viewer Node"]
    silh_thres = br.silhouette_threshold
    recover_silh = br.recover_silhouettes
    silh_scale = br.silhouette_scale
    MINS = br.min_gridsize
    smoothiterations = br.smooth_iterations
    vcycleiterations = br.vcycle_iterations
    linbcgiterations = br.linbcg_iterations
    useplanar = br.use_planar
    if br.gradient_scaling_mask_use:
        m = bpy.data.images[br.gradient_scaling_mask_name]

    nar = image_to_numpy(i)
    if br.gradient_scaling_mask_use:
        mask = image_to_numpy(m)
    # put image to scale
    tonemap(nar, br.depth_exponent)
    nar = 1 - nar  # reverse z buffer+ add something
    print(nar.min(), nar.max())
    gx = nar.copy()
    gx.fill(0)
    gx[:-1, :] = nar[1:, :] - nar[:-1, :]
    gy = nar.copy()
    gy.fill(0)
    gy[:, :-1] = nar[:, 1:] - nar[:, :-1]

    # it' ok, we can treat neg and positive silh separately here:
    a = br.attenuation
    planar = nar < (nar.min() + 0.0001)
    # sqrt for silhouettes recovery:
    sqrarx = numpy.abs(gx)
    for iter in range(0, br.silhouette_exponent):
        sqrarx = numpy.sqrt(sqrarx)
    sqrary = numpy.abs(gy)
    for iter in range(0, br.silhouette_exponent):
        sqrary = numpy.sqrt(sqrary)

    # detect and also recover silhouettes:
    silhxpos = gx > silh_thres
    gx = gx * (-silhxpos) + recover_silh * (silhxpos * silh_thres * silh_scale) * sqrarx
    silhxneg = gx < -silh_thres
    gx = gx * (-silhxneg) - recover_silh * (silhxneg * silh_thres * silh_scale) * sqrarx
    silhx = numpy.logical_or(silhxpos, silhxneg)
    gx = gx * silhx + (1.0 / a * numpy.log(1.0 + a * (gx))) * (-silhx)  # attenuate

    silhypos = gy > silh_thres
    gy = gy * (-silhypos) + recover_silh * (silhypos * silh_thres * silh_scale) * sqrary
    silhyneg = gy < -silh_thres
    gy = gy * (-silhyneg) - recover_silh * (silhyneg * silh_thres * silh_scale) * sqrary
    silhy = numpy.logical_or(silhypos, silhyneg)  # both silh
    gy = gy * silhy + (1.0 / a * numpy.log(1.0 + a * (gy))) * (-silhy)  # attenuate

    # now scale slopes...
    if br.gradient_scaling_mask_use:
        gx *= mask
        gy *= mask

    divg = gx + gy
    divga = numpy.abs(divg)
    divgp = divga > silh_thres / 4.0
    divgp = 1 - divgp
    for a in range(0, 2):
        atimes(divgp, divga)
        divga = divgp

    numpy_to_image(divga, "problem")


def relief(br):
    """Process an image to enhance relief features.

    This function takes an input image and applies various processing
    techniques to enhance the relief features based on the provided
    parameters. It utilizes gradient calculations, silhouette recovery, and
    optional detail enhancement through Fourier transforms. The processed
    image is then used to build a mesh representation.

    Args:
        br (object): An object containing various parameters for the relief processing,
            including:
            - use_image_source (bool): Whether to use a specified image source.
            - source_image_name (str): The name of the source image.
            - silhouette_threshold (float): Threshold for silhouette detection.
            - recover_silhouettes (bool): Flag to indicate if silhouettes should be
            recovered.
            - silhouette_scale (float): Scale factor for silhouette recovery.
            - min_gridsize (int): Minimum grid size for processing.
            - smooth_iterations (int): Number of iterations for smoothing.
            - vcycle_iterations (int): Number of iterations for V-cycle processing.
            - linbcg_iterations (int): Number of iterations for linear BCG
            processing.
            - use_planar (bool): Flag to indicate if planar processing should be
            used.
            - gradient_scaling_mask_use (bool): Flag to indicate if a gradient
            scaling mask should be used.
            - gradient_scaling_mask_name (str): Name of the gradient scaling mask
            image.
            - depth_exponent (float): Exponent for depth adjustment.
            - attenuation (float): Attenuation factor for the processing.
            - detail_enhancement_use (bool): Flag to indicate if detail enhancement
            should be applied.
            - detail_enhancement_freq (float): Frequency for detail enhancement.
            - detail_enhancement_amount (float): Amount of detail enhancement to
            apply.

    Returns:
        None: The function processes the image and builds a mesh but does not return a
            value.

    Raises:
        ReliefError: If the input image is blank or invalid.
    """

    t = time.time()

    if br.use_image_source:
        i = bpy.data.images[br.source_image_name]
    else:
        i = bpy.data.images["Viewer Node"]
    silh_thres = br.silhouette_threshold
    recover_silh = br.recover_silhouettes
    silh_scale = br.silhouette_scale
    MINS = br.min_gridsize
    smoothiterations = br.smooth_iterations
    vcycleiterations = br.vcycle_iterations
    linbcgiterations = br.linbcg_iterations
    useplanar = br.use_planar
    if br.gradient_scaling_mask_use:
        m = bpy.data.images[br.gradient_scaling_mask_name]

    nar = image_to_numpy(i)
    # return
    if br.gradient_scaling_mask_use:
        mask = image_to_numpy(m)
    # put image to scale
    tonemap(nar, br.depth_exponent)
    nar = 1 - nar  # reverse z buffer+ add something
    print("Range:", nar.min(), nar.max())
    if nar.min() - nar.max() == 0:
        raise ReliefError(
            "Input Image Is Blank - Check You Have the Correct View Layer or Input Image Set."
        )

    gx = nar.copy()
    gx.fill(0)
    gx[:-1, :] = nar[1:, :] - nar[:-1, :]
    gy = nar.copy()
    gy.fill(0)
    gy[:, :-1] = nar[:, 1:] - nar[:, :-1]

    # it' ok, we can treat neg and positive silh separately here:
    a = br.attenuation
    # numpy.logical_or(silhxplanar,silhyplanar)#
    planar = nar < (nar.min() + 0.0001)
    # sqrt for silhouettes recovery:
    sqrarx = numpy.abs(gx)
    for iter in range(0, br.silhouette_exponent):
        sqrarx = numpy.sqrt(sqrarx)
    sqrary = numpy.abs(gy)
    for iter in range(0, br.silhouette_exponent):
        sqrary = numpy.sqrt(sqrary)

    # detect and also recover silhouettes:
    silhxpos = gx > silh_thres
    print("*** silhxpos is %s" % silhxpos)
    gx = gx * (~silhxpos) + recover_silh * (silhxpos * silh_thres * silh_scale) * sqrarx
    silhxneg = gx < -silh_thres
    gx = gx * (~silhxneg) - recover_silh * (silhxneg * silh_thres * silh_scale) * sqrarx
    silhx = numpy.logical_or(silhxpos, silhxneg)
    gx = gx * silhx + (1.0 / a * numpy.log(1.0 + a * (gx))) * (~silhx)  # attenuate

    silhypos = gy > silh_thres
    gy = gy * (~silhypos) + recover_silh * (silhypos * silh_thres * silh_scale) * sqrary
    silhyneg = gy < -silh_thres
    gy = gy * (~silhyneg) - recover_silh * (silhyneg * silh_thres * silh_scale) * sqrary
    silhy = numpy.logical_or(silhypos, silhyneg)  # both silh
    gy = gy * silhy + (1.0 / a * numpy.log(1.0 + a * (gy))) * (~silhy)  # attenuate

    # now scale slopes...
    if br.gradient_scaling_mask_use:
        gx *= mask
        gy *= mask

    divg = gx + gy
    divg[1:, :] = divg[1:, :] - gx[:-1, :]  # subtract x
    divg[:, 1:] = divg[:, 1:] - gy[:, :-1]  # subtract y

    if br.detail_enhancement_use:  # fourier stuff here!disabled by now
        print("detail enhancement")
        rows, cols = gx.shape
        crow, ccol = int(rows / 2), int(cols / 2)

        divgmin = divg.min()
        divg += divgmin
        divgf = numpy.fft.fft2(divg)
        divgfshift = numpy.fft.fftshift(divgf)
        mask = divg.copy()
        pos = numpy.array((crow, ccol))

        def filterwindow(x, y, cx=0, cy=0):
            return abs((cx - x)) + abs((cy - y))

        mask = numpy.fromfunction(filterwindow, divg.shape, cx=crow, cy=ccol)
        mask = numpy.sqrt(mask)

        maskmin = mask.min()
        maskmax = mask.max()
        mask = (mask - maskmin) / (maskmax - maskmin)
        mask *= br.detail_enhancement_amount
        mask += 1 - mask.max()

        mask[crow - 1 : crow + 1, ccol - 1 : ccol + 1] = 1  # to preserve basic freqencies.

        divgfshift = divgfshift * mask
        divgfshift = numpy.fft.ifftshift(divgfshift)
        divg = numpy.abs(numpy.fft.ifft2(divgfshift))
        divg -= divgmin
        divg = -divg
        print("detail enhancement finished")

    levels = 0
    mins = min(nar.shape[0], nar.shape[1])
    while mins >= MINS:
        levels += 1
        mins = mins / 2

    target = numpy.zeros_like(divg)

    solve_pde_multigrid(
        divg,
        target,
        vcycleiterations,
        linbcgiterations,
        smoothiterations,
        mins,
        levels,
        useplanar,
        planar,
    )

    tonemap(target, 1)

    build_mesh(target, br)

    t = time.time() - t
    print("total time:" + str(t) + "\n")
