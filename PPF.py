import numpy as np
from scipy import signal

"""
Contains all the different functions required for the application
to apply the functions on the data uploaded.
"""

def derivative(t: list, x: list) -> np.ndarray:
    """
    Derivation of a signal.

    :param t: Time array
    :param x: Signal array
    :return: Array containing the derivative of the signal 'x'.
    """
    h = t[1] - t[0]
    y = np.zeros(len(t))
    i = 0
    while i <= len(x) - 1:
        y[i] = (x[i] - x[i - 1]) / h
        i = i + 1
    return y


def integration(t: list, x: list) -> np.ndarray:
    """
    Integration of a signal.

    :param t: Time array
    :param x: Signal array
    :return: Array containing the integration of the signal 'x'.
    """
    h = t[1] - t[0]
    y = np.zeros(len(t))
    i = 1
    while i <= len(x) - 1:
        y[i] = y[i - 1] + h * (x[i - 1])
        i = i + 1
    return y

# -------------------------------------------------------------------------------

def myhighpass(t: list, u: list, tc: float) -> np.ndarray:
    """
    First order high pass filter.

    :param t: Time array
    :param u: Signal array
    :param tc: Cut-off frequency for the filter
    :return: Array showing the high-pass output of signal 'x' based on cutoff frequency 'tc'.
    """
    tc = 1/(2 * np.pi * tc)
    x = [u[0]]
    y = np.zeros(len(t))
    h = t[1] - t[0]
    for i in range(len(t) - 1):
        y1 = (x[i] + (h / tc * u[i + 1])) / (1 + h / tc)
        x.append(y1)
    for k in range(len(t)):
        y[k] = -x[k] + u[k]
    return y


def mylowpass(t: list, u: list, tc: float) -> np.ndarray:
    """
    First order low pass filter.

    :param t: Time array
    :param u: Signal array
    :param tc: Cut-off frequency for the filter
    :return: Array showing the low-pass output of signal 'x' based on cutoff frequency 'tc'.
    """
    tc = 1/(2 * np.pi * tc)
    x = [u[0]]
    y = np.zeros(len(t))
    h = t[1] - t[0]
    for i in range(len(t) - 1):
        y1 = (x[i] + (h / tc * u[i + 1])) / (1 + h / tc)
        x.append(y1)
    for k in range(len(t)):
        y[k] = x[k]
    return y

# -------------------------------------------------------------------------------

def mw_dft(data: list, t: list, omega: float) -> complex:
    """
    Moving discrete fourier transform

    :param data: Signal whose dft needs to be calculated
    :param t: Time signal
    :param omega: Dominant frequency
    :return: Complex number
    """
    win_len = len(t)
    X_data = np.zeros(len(t))
    X_data = sum(X_data + data * np.exp((-omega * t * 1j)))
    X_data = np.sqrt(2) / win_len * X_data
    return X_data


def window_phasor(x: list, t: list, sr: int, cycles: float) -> [np.ndarray, np.ndarray]:
    """
    Moving discrete fourier transform.

    :param x: Signal array
    :param t: Time array
    :param sr: Down-sampling factor
    :param cycles: Window length as per number of cycles
    :return: A complex number array of calculated fundamental phasor.
    """
    va = x[0::sr]
    t = t[0::sr]
    h = t[1] - t[0]
    tnew = t

    va_mw = np.zeros(len(va), dtype='complex_')
    dom_freq = 50
    period = round(cycles / (dom_freq * h))

    for i in range(period, len(t)):
        va_mw[i] = mw_dft(va[i - period:i], t[i - period:i], dom_freq * 2 * np.pi)
    return [va_mw, tnew]


def freq4mdft(va: list, t: list, sr: int, cycles: float, dominant_frequency: float) -> [np.ndarray, np.ndarray, np.ndarray]:
    """
    ***
    :param dominant_frequency:
    :param va:
    :param t:
    :param sr:
    :param cycles:
    :return:
    """
    va = va[::sr]
    t = t[::sr]
    tnew = t
    h = t[1] - t[0]
    tnew = np.array(tnew, dtype='complex_')

    va_mw = np.zeros(len(va), dtype='complex_')
    dom_freq = dominant_frequency
    period = round(cycles / (dom_freq * h))

    # Note index starts from zero and not one!!
    for i in range(period, len(t)):
        va_mw[i] = mw_dft(va[i - period:i], t[i - period:i], dom_freq * 2 * np.pi)
    Vmw = va_mw

    va_r = np.real(va_mw)
    va_im = np.imag(va_mw)
    freq_a = np.zeros(len(Vmw), dtype='complex_')
    np.seterr(invalid='ignore')
    va_r_dot_l1 = [0]
    va_im_dot_l1 = [0]
    for i in range(0, len(va_r) - 1):
        freq_a[i] = np.real(50 + ((va_r[i] * va_im_dot_l1[i]) - (va_im[i] * va_r_dot_l1[i])) / ((
                                                                                                        va_r[i] ** 2 +
                                                                                                        va_im[
                                                                                                            i] ** 2) * (
                                                                                                            2 * np.pi)))
        va_r_dot = (va_r[i + 1] - va_r[i]) / h
        va_im_dot = (va_im[i + 1] - va_im[i]) / h
        va_r_dot_l1.append(va_r_dot)
        va_im_dot_l1.append(va_im_dot)

    # Last element is becoming 0 for some reason
    freq_a[-1] = freq_a[-2]

    fa = np.zeros(len(freq_a), dtype='complex_')
    dom_freq = 50
    period = round(cycles / (dom_freq * h))

    for i in range(period, len(t)):
        fa[i] = (mw_dft(freq_a[i - period:i], t[i - period:i], 0)) / np.sqrt(2)

    return [fa, tnew, freq_a]


def freq4mdftPhasor(va: list, t: list, cycles: float) -> [np.ndarray, np.ndarray, np.ndarray]:
    """
    ***
    :param va:
    :param t:
    :param cycles:
    :return:
    """
    sr = 1
    va = va[::sr]
    t = t[::sr]

    h = t[1] - t[0]

    va_r = np.real(va)
    va_im = np.imag(va)
    freq_a = np.zeros(len(va_r), dtype='complex_')
    np.seterr(invalid='ignore')
    va_r_dot_l1 = [0]
    va_im_dot_l1 = [0]
    for i in range(1, len(va_r)):
        freq_a[i - 1] = np.real(50 + ((va_r[i - 1] * va_im_dot_l1[i - 1]) - (va_im[i - 1] * va_r_dot_l1[i - 1])) / (
                    (va_r[i - 1] ** 2 + va_im[i - 1] ** 2) * (2 * np.pi)))
        va_r_dot = (va_r[i] - va_r[i - 1]) / h
        va_im_dot = (va_im[i] - va_im[i - 1]) / h
        va_r_dot_l1.append(va_r_dot)
        va_im_dot_l1.append(va_im_dot)
    freq_a[-1] = freq_a[-2]

    fa = np.zeros(len(freq_a), dtype='complex_')
    dom_freq = 50
    period = round(cycles / (dom_freq * h))

    for i in range(period, len(t)):
        fa[i] = (mw_dft(freq_a[i - period:i], t[i - period:i], 0)) / np.sqrt(2)

    return [fa, t, freq_a]

# -------------------------------------------------------------------------------

def instant_power(va: list, vb: list, vc: list, ia: list, ib: list, ic: list) -> [np.ndarray, np.ndarray]:
    p = np.zeros(len(va))
    q = np.zeros(len(va))
    for i in range(len(va)):
        p[i] = va[i] * ia[i] + vb[i] * ib[i] + vc[i] * ic[i]
        q[i] = (1 / np.sqrt(3)) * ((va[i] - vb[i]) * ic[i] + (vb[i] - vc[i]) * ia[i] + (vc[i] - va[i]) * ib[i])
    return [p, q]


def line_current(ia: list, ib: list, ic: list) -> np.ndarray:
    I = np.zeros(len(ia))
    for i in range(len(ia)):
        I[i] = (np.sqrt(ia[i] ** 2 + ib[i] ** 2 + ic[i] ** 2)) / np.sqrt(3)
    return I


def line_voltage(va: list, vb: list, vc: list) -> np.ndarray:
    V = np.zeros(len(va))
    for i in range(len(va)):
        V[i] = np.sqrt((va[i]) ** 2 + (vb[i]) ** 2 + (vc[i]) ** 2)
    return V

# -------------------------------------------------------------------------------

def clarkestranform(t: list, va: list, vb: list, vc: list):
    mat = [[1, 0, np.sqrt(0.5)],
           [-0.5, -np.sqrt(3) / 2, np.sqrt(0.5)],
           [-0.5, np.sqrt(3) / 2, np.sqrt(0.5)]]
    mat = np.array(mat)
    B = np.linalg.inv(np.sqrt(2 / 3) * mat)
    fabg = np.zeros([3, len(t)])
    for i in range(len(t)):
        for k in range(np.shape(fabg)[0]):
            fabg[k][i] = np.dot(B, [[va[i]], [vb[i]], [vc[i]]])[k]
    return [fabg[0], fabg[1], fabg[2]]

def inv_clarkestransform(t: list, va: list, vb: list, vc: list):
    mat = [[1, -0.5, -0.5],
           [0, -np.sqrt(3) / 2, np.sqrt(3) / 2],
           [np.sqrt(0.5), np.sqrt(0.5), np.sqrt(0.5)]]
    mat = np.array(mat)
    B = np.linalg.inv(np.sqrt(2 / 3) * mat)
    fabg = np.zeros([3, len(t)])
    for i in range(len(t)):
        for k in range(np.shape(fabg)[0]):
            fabg[k][i] = np.dot(B, [[va[i]], [vb[i]], [vc[i]]])[k]
    return [fabg[0], fabg[1], fabg[2]]

def parkstransform(t: list, va: list, vb: list, vc: list, w: float, gamma: float):
    w1 = 2 * np.pi * w
    fdqo = np.zeros([3, len(t)])
    for i in range(len(t)):
        a = (w1 * t[i]) + gamma
        mat = [[np.cos(a), np.cos(a - (2 * np.pi / 3)), np.cos(a - (4 * np.pi / 3))],
               [np.sin(a), np.sin(a - (2 * np.pi / 3)), np.sin(a - (4 * np.pi / 3))],
               [np.sqrt(0.5), np.sqrt(0.5), np.sqrt(0.5)]]
        mat = np.array(mat)
        B = np.sqrt(2 / 3) * mat
        for k in range(np.shape(fdqo)[0]):
            fdqo[k][i] = np.dot(B, [[va[i]], [vb[i]], [vc[i]]])[k]
    return [fdqo[0], fdqo[1], fdqo[2]]

def inv_parkstransform(t: list, va: list, vb: list, vc: list, w: float, gamma: float):
    w1 = 2 * np.pi * w
    fdqo = np.zeros([3, len(t)])
    for i in range(len(t)):
        a = (w1 * t[i]) + gamma
        mat = [[np.cos(a), np.sin(a), np.sqrt(0.5)],
               [np.cos(a - (2 * np.pi / 3)), np.sin(a - (2 * np.pi / 3)), np.sqrt(0.5)],
               [np.cos(a - (4 * np.pi / 3)), np.sin(a - (4 * np.pi / 3)), np.sqrt(0.5)]]
        mat = np.array(mat)
        B = np.sqrt(2 / 3) * mat
        for k in range(np.shape(fdqo)[0]):
            fdqo[k][i] = np.dot(B, [[va[i]], [vb[i]], [vc[i]]])[k]
    return [fdqo[0], fdqo[1], fdqo[2]]

def sequencetransform(t: list, va: list, vb: list, vc: list):
    """
    :param t:
    :param va:
    :param vb:
    :param vc:
    :return: 3 arrays corresponding to positive, negative, zero sequence respectively
    """
    a = np.exp(2 * np.pi * 1j / 3)
    mat = [[1, 1, 1],
           [a ** 2, a, 1],
           [a, a ** 2, 1]]
    mat = np.array(mat)
    B = np.linalg.inv(mat)
    fpno = np.zeros([3, len(t)], dtype='complex_')
    for i in range(len(t)):
        for k in range(np.shape(fpno)[0]):
            fpno[k][i] = np.dot(B, [[va[i]], [vb[i]], [vc[i]]])[k]
    return [fpno[0], fpno[1], fpno[2]]

# -------------------------------------------------------------------------------

def xcorr(signal1: np.ndarray, signal2: np.ndarray) -> [np.ndarray, np.ndarray]:
    """
    Correlation of 2 signals, covariance of 'Signal 2' w.r.t. 'Signal 1'.

            Parameters:
                    signal1 (numpy.ndarray): Signal 1 array
                    signal2 (numpy.ndarray): Signal 2 array
            Returns:
                    lags (numpy.ndarray): Array ranging from -len(signal) to len(signal)
                    corr (numpy.ndarray): Correlation of signal2 w.r.t signal1
    
    To calculate the point of max correlation use following:
        index_of_max_correlation = lag[corr.argmax()]
        
    For actual difference in time:
        time_difference_between_signal = lag[corr.argmax()]*h
        Here, h: Time step of signal1
    """
    corr = signal.correlate(signal1, signal2, mode="full")
    lags = signal.correlation_lags(len(signal1), len(signal2), mode="full")
    return lags, corr

def xcov(signal1: np.ndarray, signal2: np.ndarray) -> [np.ndarray, np.ndarray]:
    """
    Covariance of 2 signals, covariance of 'Signal 2' w.r.t. 'Signal 1'.

            Parameters:
                    signal1 (numpy.ndarray): Signal 1 array
                    signal2 (numpy.ndarray): Signal 2 array
            Returns:
                    lags (numpy.ndarray): Array ranging from -len(signal) to len(signal)
                    cov (numpy.ndarray): Covariance of signal2 w.r.t signal1
    
    To calculate the point of max covariance use following:
        index_of_max_covariance = lag[cov.argmax()]
        
    For actual difference in time:
        time_difference_between_signal = lag[cov.argmax()]*h
        Here, h: Time step of signal1
    """
    cov = signal.correlate(signal1 - np.mean(signal1), signal2 - np.mean(signal2), mode="full")
    lags = signal.correlation_lags(len(signal1), len(signal2), mode="full")
    return lags, cov

# -------------------------------------------------------------------------------

def trendfilter(t: list, x: list, lambda1=1) -> np.ndarray:
    # New version, uses sparse matrix is very efficient from the older version.
    """
    Returns the overall trend of the input signal based on the smoothening factor 'lambda1'.

    :param t: Time array
    :type t: numpy.ndarray | list
    :param x: Signal array
    :type x: numpy.ndarray | list
    :param lambda1: Hyper-parameter, decides order of smoothening
    :type lambda1: int

    :return: Array containing trend of the signal based on 'lambda1'.
    :rtype: numpy.ndarray
    """
    from scipy import sparse
    from statsmodels.tools.validation import array_like, PandasWrapper
    from scipy.sparse.linalg import spsolve

    pw = PandasWrapper(x)
    nobs = len(t)
    I = sparse.eye(nobs, nobs)
    offsets = np.array([0, 1, 2])
    data = np.repeat([[1.], [-2.], [1.]], nobs, axis=1)
    K = sparse.dia_matrix((data, offsets), shape=(nobs - 2, nobs))
    
    use_umfpack = True
    trend = spsolve(I+lambda1*K.T.dot(K), x, use_umfpack=use_umfpack)

    return pw.wrap(trend, append='trend')

# -------------------------------------------------------------------------------

def avgMovWin(t: list, v: list, t_win: int) -> np.ndarray:
    """
    Average of signal taken over a moving window.

    :param t: Time array
    :param v: Signal array
    :param t_win: Length of the time window.
    :return: Average of signal using a moving window.
    """
    N = len(t)
    h = t[1] - t[0]
    tw = t_win / h

    avg = np.zeros(N)

    for i in range(int(tw), N):
        sum1 = 0
        for j in range(int(i - tw), i):
            sum1 += v[j]
            avg[i] = sum1 / tw

    return avg

# -------------------------------------------------------------------------------

def rmsMovWin(t: list, v: list, t_win: int):
    """
    RMS of signal taken over a moving window.

    :param t: Time array
    :param v: Signal array
    :param t_win: Length of the time window.
    :return: RMS of signal using a moving window.
    """
    N = len(t)
    h = t[1] - t[0]
    tw = t_win / h

    rms = np.zeros(N)

    for i in range(int(tw), N):
        sum1 = 0
        for j in range(int(i - tw), i):
            sum1 += v[j] ** 2
        rms[i] = np.sqrt(sum1 / tw)

    return rms

# -------------------------------------------------------------------------------

def instaLL_RMSVoltage(t: list, va: list, vb: list, vc: list):
    v_rms = np.zeros(len(t))
    for i in range(len(t)):
        v_rms[i] = np.sqrt(va[i]**2 + vb[i]**2 + vc[i]**2)
    return v_rms

def insta_RMSCurrent(t: list, ia: list, ib: list, ic: list):
    i_rms = np.zeros(len(t))
    for i in range(len(t)):
        i_rms[i] = (1/np.sqrt(3)) * np.sqrt(ia[i]**2 + ib[i]**2 + ic[i]**2)
    return i_rms

def impedance(va: list, vb: list, vc: list, ia: list, ib: list, ic: list):
    va = np.array(va)
    vb = np.array(vb)
    vc = np.array(vc)
    ia = np.array(ia)
    ib = np.array(ib)
    ic = np.array(ic)

    Z = np.sqrt(va**2 + vb**2 + vc**2) / np.sqrt(ia**2 + ib**2 + ic**2)

    return Z