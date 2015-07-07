#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Various reflectivity algorithms.

:copyright: 2015 Agile Geoscience
:license: Apache 2.0
"""
import numpy as np
from numpy import tan, sin, cos

from .moduli import pr

def scattering_matrix(vp1, vs1, rho1, vp0, vs0, rho0, theta1):
    '''
    Full Zoeppritz solution, considered the definitive solution.
    Calculates the angle dependent p-wave reflectivity of an interface
    between two mediums.

    Written by: Wes Hamlyn

    :param vp1: The p-wave velocity of the upper medium.
    :param vs1: The s-wave velocity of the upper medium.
    :param rho1: The density of the upper medium.

    :param vp0: The p-wave velocity of the lower medium.
    :param vs0: The s-wave velocity of the lower medium.
    :param rho0: The density of the lower medium.

    :param theta1: A scalar  [degrees].

    :returns: a 4x4 array representing the scattering matrix
                at the incident angle theta1.
    '''
    # Make sure theta1 is an array
    theta1 = np.radians(np.array(theta1))
    if theta1.size == 1:
        theta1 = np.expand_dims(theta1, axis=1)

    # Set the ray paramter, p
    p = sin(theta1) / vp1  # ray parameter

    # Calculate reflection & transmission angles for Zoeppritz
    theta1 = np.radians(theta1)   # Convert theta1 to radians
    theta2 = np.arcsin(p * vp0)      # Trans. angle of P-wave
    phi1 = np.arcsin(p * vs1)     # Refl. angle of converted S-wave
    phi2 = np.arcsin(p * vs0)      # Trans. angle of converted S-wave

    # Matrix form of Zoeppritz Equations... M & N are matricies
    M = np.array([[-sin(theta1), -cos(phi1), sin(theta2), cos(phi2)],
                  [cos(theta1), -sin(phi1), cos(theta2), -sin(phi2)],
                  [2 * rho1 * vs1 * sin(phi1) * cos(theta1),
                   rho1 * vs1 * (1 - 2 * sin(phi1) ** 2),
                   2 * rho0 * vs0 * sin(phi2) * cos(theta2),
                   rho0 * vs0 * (1 - 2 * sin(phi2) ** 2)],
                  [-rho1 * vp1 * (1 - 2 * sin(phi1) ** 2),
                   rho1 * vs1 * sin(2 * phi1),
                   rho0 * vp0 * (1 - 2 * sin(phi2) ** 2),
                   -rho0 * vs0 * sin(2 * phi2)]], dtype='float')

    N = np.array([[sin(theta1), cos(phi1), -sin(theta2), -cos(phi2)],
                  [cos(theta1), -sin(phi1), cos(theta2), -sin(phi2)],
                  [2 * rho1 * vs1 * sin(phi1) * cos(theta1),
                   rho1 * vs1 * (1 - 2 * sin(phi1) ** 2),
                   2 * rho0 * vs0 * sin(phi2) * cos(theta2),
                   rho0 * vs0 * (1 - 2 * sin(phi2) ** 2)],
                  [rho1 * vp1 * (1 - 2 * sin(phi1) ** 2),
                   -rho1 * vs1 * sin(2 * phi1),
                   - rho0 * vp0 * (1 - 2 * sin(phi2) ** 2),
                   rho0 * vs0 * sin(2 * phi2)]], dtype='float')

    zoep = np.zeros((4, 4, M.shape[-1]))
    for i in range(M.shape[-1]):
        Mi = M[..., i]
        Ni = N[..., i]
        dt = np.dot(np.linalg.inv(Mi), Ni)
        zoep[..., i] = dt

    return zoep


def zoeppritz_element(vp1, vs1, rho1, vp0, vs0, rho0, theta1, element='PdPu'):
    """
    Returns any mode reflection coefficients from the Zoeppritz
    scattering matrix. Pass in the mode as element, e.g. 'PdSu' for PS.

    Wraps scattering_matrix().

    :returns: a vector of len(theta1) containing the reflectivity
             value corresponding to each angle.
    """
    elements = np.array([['PdPu', 'SdPu', 'PuPu', 'SuPu'],
                         ['PdSu', 'SdSu', 'PuSu', 'SuSu'],
                         ['PdPd', 'SdPd', 'PuPd', 'SuPd'],
                         ['PdSd', 'SdSd', 'PuSd', 'SuSd']])

    Z = scattering_matrix(vp1, vs1, rho1, vp0, vs0, rho0, theta1)

    return np.squeeze(Z[np.where(elements == element)])


def zoeppritz(vp1, vs1, rho1, vp0, vs0, rho0, theta1):
    '''
    Returns the PP reflection coefficients from the Zoeppritz
    scattering matrix.

    Wraps zoeppritz_element().

    :returns: a vector of len(theta1) containing the reflectivity
             value corresponding to each angle.
    '''
    return zoeppritz_element(vp1, vs1, rho1, vp0, vs0, rho0, theta1, 'PdPu')


def akirichards(vp1, vs1, rho1, vp2, vs2, rho2, theta1, terms=False):
    """
    This is the formulation from Avseth et al.,
    Quantitative seismic interpretation,
    Cambridge University Press, 2006. Adapted for a 4-term formula.
    See http://subsurfwiki.org/wiki/Aki-Richards_equation

    :param vp1: The p-wave velocity of the upper medium.
    :param vs1: The s-wave velocity of the upper medium.
    :param rho1: The density of the upper medium.

    :param vp2: The p-wave velocity of the lower medium.
    :param vs2: The s-wave velocity of the lower medium.
    :param rho2: The density of the lower medium.

    :param theta1: An array of incident angles to use for reflectivity
                   calculation [degrees].

    :returns: a vector of len(theta1) containing the reflectivity
             value corresponding to each angle
    """

    # We are not using this for anything, but will
    # critical_angle = arcsin(vp1/vp2)

    # Do we need to ensure that we get floats out before
    # computing sines?
    if np.ndim(vp1) == 0:
        vp1 = float(vp1)
    else:
        vp1 = np.array(vp1).astype(float)

    theta1 = np.radians(theta1)
    theta2 = np.arcsin(vp2/vp1*sin(theta1))

    # Compute the various parameters
    drho = rho2-rho1
    dvp = vp2-vp1
    dvs = vs2-vs1
    meantheta = (theta1+theta2) / 2.0
    rho = (rho1+rho2) / 2.0
    vp = (vp1+vp2) / 2.0
    vs = (vs1+vs2) / 2.0

    # Compute the coefficients
    w = 0.5 * drho/rho
    x = 2 * (vs/vp1)**2 * drho/rho
    y = 0.5 * (dvp/vp)
    z = 4 * (vs/vp1)**2 * (dvs/vs)

    # Compute the terms
    term1 = w
    term2 = -1 * x * sin(theta1)**2
    term3 = y / cos(meantheta)**2
    term4 = -1 * z * sin(theta1)**2

    if terms:
        return term1, term2, term3, term4
    else:
        return (term1 + term2 + term3 + term4)


def akirichards_alt(vp1, vs1, rho1, vp2, vs2, rho2, theta1):
    """
    This is another formulation of the Aki-Richards solution.
    See http://subsurfwiki.org/wiki/Aki-Richards_equation

    :param vp1: The p-wave velocity of the upper medium.
    :param vs1: The s-wave velocity of the upper medium.
    :param rho1: The density of the upper medium.

    :param vp2: The p-wave velocity of the lower medium.
    :param vs2: The s-wave velocity of the lower medium.
    :param rho2: The density of the lower medium.

    :param theta1: An array of incident angles to use for reflectivity
                   calculation [degrees].

    :returns: a vector of len(theta1) containing the reflectivity
             value corresponding to each angle.
    """

    # We are not using this for anything, but will
    # critical_angle = arcsin(vp1/vp2)

    # Do we need to ensure that we get floats out before
    # computing sines?
    if np.ndim(vp1) == 0:
        vp1 = float(vp1)
    else:
        vp1 = np.array(vp1).astype(float)

    theta1 = np.radians(theta1)
    theta2 = np.arcsin(vp2/vp1*sin(theta1))

    # Compute the various parameters
    drho = rho2-rho1
    dvp = vp2-vp1
    dvs = vs2-vs1
    theta = (theta1+theta2)/2.0
    rho = (rho1+rho2)/2.0
    vp = (vp1+vp2)/2.0
    vs = (vs1+vs2)/2.0

    # Compute the three terms
    term1 = 0.5 * (dvp/vp + drho/rho)
    term2 = (0.5*dvp/vp-2*(vs/vp)**2*(drho/rho+2*dvs/vs)) * sin(theta)**2
    term3 = 0.5 * dvp/vp * (tan(theta)**2 - sin(theta)**2)

    if terms:
        return term1, term2, term3
    else:
        return (term1 + term2 + term3)

def fatti(vp1, vs1, rho1, vp2, vs2, rho2, theta1):
    """
    Compute reflectivities with Fatti's formulation of the
    Aki-Richards equation, which does not account for the
    critical angle. Fatti et al (1994), Geophysics 59 (9).

    :param vp1: The p-wave velocity of the upper medium.
    :param vs1: The s-wave velocity of the upper medium.
    :param rho1: The density of the upper medium.

    :param vp2: The p-wave velocity of the lower medium.
    :param vs2: The s-wave velocity of the lower medium.
    :param rho2: The density of the lower medium.

    :param theta1: An array of incident angles to use for reflectivity
                   calculation [degrees].

    :returns: a vector of len(theta1) containing the reflectivity
             value corresponding to each angle.
    """
    # Do we need to ensure that we get floats out before computing
    # sines?
    if np.ndim(vp1) == 0:
        vp1 = float(vp1)
    else:
        vp1 = np.array(vp1).astype(float)

    theta1 = np.radians(theta1)

    # Compute the various parameters
    drho = rho2-rho1
    rho = (rho1+rho2) / 2.0
    vp = (vp1+vp2) / 2.0
    vs = (vs1+vs2) / 2.0
    dip = (vp2*rho2 - vp1*rho1)/(vp2*rho2 + vp1*rho1)
    dis = (vs2*rho2 - vs1*rho1)/(vs2*rho2 + vs1*rho1)
    d = drho/rho

    # Compute the three terms
    term1 = (1 + tan(theta1)**2) * dip
    term2 = -8 * (vs/vp)**2 * sin(theta1)**2 * dis
    term3 = -1 * (0.5 * tan(theta1)**2 - 2 * (vs/vp)**2 * sin(theta1)**2) * d

    if terms:
        return term1, term2, term3
    else:
        return (term1 + term2 + term3)

def shuey(vp1, vs1, rho1, vp2, vs2, rho2, theta1, terms=False):
    """
    Compute Shuey approximation with 3 terms.
    http://subsurfwiki.org/wiki/Shuey_equation

    :param vp1: The p-wave velocity of the upper medium.
    :param vs1: The s-wave velocity of the upper medium.
    :param rho1: The density of the upper medium.

    :param vp2: The p-wave velocity of the lower medium.
    :param vs2: The s-wave velocity of the lower medium.
    :param rho2: The density of the lower medium.

    :param theta1: An array of incident angles to use for reflectivity
                   calculation [degrees].

    :returns: a vector of len(theta1) containing the reflectivity
             value corresponding to each angle.
    """
    theta1 = np.radians(theta1)

    # Compute some parameters
    drho = rho2-rho1
    dvp = vp2-vp1
    dvs = vs2-vs1
    rho = (rho1+rho2)/2.0
    vp = (vp1+vp2)/2.0
    vs = (vs1+vs2)/2.0

    # Compute three-term reflectivity

    r0 = 0.5 * (dvp/vp + drho/rho)
    g = 0.5 * dvp/vp - 2 * (vs**2/vp**2) * (drho/rho + 2 * dvs/vs)
    f = 0.5 * dvp/vp

    term1 = r0
    term2 = g * np.sin(theta1)**2
    term3 = f * (np.tan(theta1)**2 - np.sin(theta1)**2)

    if terms:
        return term1, term2, term3
    else:
        return (term1 + term2 + term3)

def shuey2(vp1, vs1, rho1, vp2, vs2, rho2, theta1, terms=False):
    """
    Compute Shuey approximation with 2 terms.

    Wraps shuey().
    """
    r0, rg, rf = shuey(vp1, vs1, rho1, vp2, vs2, rho2, theta1, terms=True)

    if terms:
        return r0, rg
    else:
        return r0 + rg

def shuey3(vp1, vs1, rho1, vp2, vs2, rho2, theta1, terms=False):
    """
    Compute Shuey approximation with 2 terms.

    Wraps shuey().
    """
    r0, rg, rf = shuey(vp1, vs1, rho1, vp2, vs2, rho2, theta1, terms=True)
    
    if terms:
        return r0, rg, rf
    else:
        return r0 + rg + rf

def bortfeld2(vp1, vs1, rho1, vp2, vs2, rho2, theta1, terms=False):
    """
    The 2-term Bortfeld approximation for ava analysis.

    :param vp1: The p-wave velocity of the upper medium.
    :param vs1: The s-wave velocity of the upper medium.
    :param rho1: The density of the upper medium.

    :param vp2: The p-wave velocity of the lower medium.
    :param vs2: The s-wave velocity of the lower medium.
    :param rho2: The density of the lower medium.

    :param theta1: An array of incident angles to use for reflectivity
                   calculation [degrees].

    :returns: a vector of len(theta1) containing the reflectivity
             value corresponding to each angle.
    """
    theta1 = np.radians(theta1)
    # Bortfeld only needs one extra parameter
    theta2 = np.arcsin(vp2/vp1*np.sin(theta1))  # radians

    # This breaks if theta = 90 deg
    term1 = 0.5 * np.log((vp2*rho2*cos(theta1)) / (vp1*rho1*cos(theta2)))

    svp2 = (np.sin(theta1)/vp1)**2
    dvs2 = (vs1**2-vs2**2)
    term2 = svp2 * dvs2 * (2+np.log(rho2/rho1)/np.log(vs2/vs1))

    if terms:
        return term1, term2
    else:
        return (term1 + term2)

def bortfeld3(vp1, vs1, rho1, vp2, vs2, rho2, theta1, terms=False):
    """
    Compute Bortfeld approximation with three terms.
    http://sepwww.stanford.edu/public/docs/sep111/marie2/paper_html/node2.html

    :param vp1: The p-wave velocity of the upper medium.
    :param vs1: The s-wave velocity of the upper medium.
    :param rho1: The density of the upper medium.

    :param vp2: The p-wave velocity of the lower medium.
    :param vs2: The s-wave velocity of the lower medium.
    :param rho2: The density of the lower medium.

    :param theta1: An array of incident angles to use for reflectivity
                   calculation [degrees].

    :returns: a vector of len(theta1) containing the reflectivity
             value corresponding to each angle.
    """
    theta1 = np.radians(theta1)

    # Compute some parameters
    drho = rho2-rho1
    dvp = vp2-vp1
    dvs = vs2-vs1
    rho = (rho1+rho2)/2.0
    vp = (vp1+vp2)/2.0
    vs = (vs1+vs2)/2.0
    k = (2 * vs/vp)**2
    rsh = 0.5 * (dvp/vp - k*drho/rho - 2*k*dvs/vs)

    # Compute three-term reflectivity
    term1 = 0.5 * (dvp/vp + drho/rho)
    term2 = rsh * np.sin(theta1)**2
    term3 = 0.5 * dvp/vp * np.tan(theta1)**2 * np.sin(theta1)**2

    if terms:
        return term1, term2, term3
    else:
        return (term1 + term2 + term3)

def hilterman(vp1, vs1, rho1, vp2, vs2, rho2, theta1):
    """
    Hilterman (1989) approximation.
    According to Dvorkin: "arguably the simplest and a very convenient
    [approximation]." At least for small angles and small contrasts.

    :param vp1: The p-wave velocity of the upper medium.
    :param vs1: The s-wave velocity of the upper medium.
    :param rho1: The density of the upper medium.

    :param vp2: The p-wave velocity of the lower medium.
    :param vs2: The s-wave velocity of the lower medium.
    :param rho2: The density of the lower medium.

    :param theta1: An array of incident angles to use for reflectivity
                   calculation [degrees].

    :returns: a vector of len(theta1) containing the reflectivity
             value corresponding to each angle.
    """
    theta1 = np.radians(theta1)
    ip1 = vp1 * rho1
    ip2 = vp2 * rho2
    rpp0 = (ip2 - ip1) / (ip2 + ip1)
    dpr = pr(vp2, vs2) - pr(vp1, vs1)

    term1 = rpp0
    term2 = 2.25*(dpr - rpp0)*np.sin(theta1)**2

    if terms:
        return term1, term2
    else:
        return (term1 + term2)

def elastic_impedance(vp, vs, rho, theta1, normalize=True):
    """
    Returns the elastic impedance (as defined by Connolly, 1999)
    for each incidence angle in theta1:

    :param vp1: The p-wave velocity or p-wave velocity array.
    :param vs1: The s-wave velocity of s-wave velocity array.
    :param rho1: The density (either scalar or array).
    :param theta1: An array of incident angles to use for reflectivity
        calculation [degrees].
    :param normalized: if True, returns the normalized form from
        Whitcombe et. al (2001).
    """
    theta1 = np.radians(theta1)
    k = (np.mean(vs) / np.mean(vp)) ** 2  # avg over interval of interest
    a = 1 + (np.tan(theta1)) ** 2
    b = -8 * k * ((np.sin(theta1)) ** 2)
    c = 1 - 4 * k * ((np.sin(theta1)) ** 2)
    ei = (vp ** a) * (vs ** b) * (rho ** c)

    if normalize:
        n = vp **(1-a) * vs**(-b) * rho**(1-c)
        ei = n * ei

    return ei
