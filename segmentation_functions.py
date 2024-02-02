import pandas as pd
import numpy as np
import PPF as ppf


def trendfilter(t, x, lambda1=1):
    from scipy import sparse
    from statsmodels.tools.validation import array_like, PandasWrapper
    from scipy.sparse.linalg import spsolve

    time = t
    pw = PandasWrapper(x)
    nobs = len(t)
    I = sparse.eye(nobs, nobs)
    offsets = np.array([0, 1, 2])
    data = np.repeat([[1.], [-2.], [1.]], nobs, axis=1)
    K = sparse.dia_matrix((data, offsets), shape=(nobs - 2, nobs))

    use_umfpack = True
    trend = spsolve(I + lambda1 * K.T.dot(K), x, use_umfpack=use_umfpack)

    return pw.wrap(trend, append='trend'), time


################################################################################################


def segmentation_trendfilter(time_signal, data_signal, lambda1=1):
    time_signal = list(time_signal)
    data_signal = list(data_signal)

    y, t = trendfilter(time_signal, data_signal)
    # z1 = abs(ppf.derivative(time_signal, data_signal))

    # Calculating the error and setting threshold
    z1 = abs(data_signal - y)

    threshold = 5 * np.mean(abs(z1) + np.std(abs(z1)))  # Setting the threshold
    z = [n for n in range(len(z1)) if z1[n] > threshold]

    # Storing the different pairs of samples which are above threshold
    v = []
    for i in range(1, len(z)):
        b = []
        if z[i] - z[i - 1] < 15:  # The "10" here needs to be dynamic? or somehow smart!!!
            b.append([z[i - 1], z[i]])
        v.append(b)

    q = [v[r][0] for r in range(len(v)) if v[r] != []]  # Removing all the empty lists from "v"

    # All different pairs input, but making a list which consist of all the samples which are close to each other
    for i in range(1, len(q)):
        if q[i][1] - q[i - 1][1] < 15:  # The "5" here needs to be dynamic? or somehow smart!!!
            q[i].extend(q[i - 1])

    # Sorting all the different pairs to remove duplicate points
    for i in range(len(q)):
        q[i] = sorted(list(set(q[i])))

    # Removing the duplicate points
    for i in range(1, len(q)):
        if q[i - 1][0] == q[i][0]:
            if len(q[i]) > len(q[i - 1]):
                q[i - 1] = None
    # Output here will be list of samples which are the starting and end of the high notch

    # Removing the irrelevant values
    q = [q[i] for i in range(len(q)) if q[i] is not None]

    # Plotting the segment start and end points
    return q, z1, threshold


###########################################################################################################
def manual_segmentation_trendfilter(time_signal, data_signal, threshold):
    time_signal = list(time_signal)
    data_signal = list(data_signal)

    y, t = trendfilter(time_signal, data_signal)

    # Calculating the error and setting threshold
    z1 = abs(data_signal - y)

    z = [n for n in range(len(z1)) if z1[n] > threshold]

    # Storing the different pairs of samples which are above threshold
    v = []
    for i in range(1, len(z)):
        b = []
        if z[i] - z[i - 1] < 20:  # The "10" here needs to be dynamic? or somehow smart!!!
            b.append([z[i - 1], z[i]])
        v.append(b)

    q = [v[r][0] for r in range(len(v)) if v[r] != []]  # Removing all the empty lists from "v"

    # All different pairs input, but making a list which consist of all the samples which are close to each other
    for i in range(1, len(q)):
        if q[i][1] - q[i - 1][1] < 20:  # The "5" here needs to be dynamic? or somehow smart!!!
            q[i].extend(q[i - 1])

    # Sorting all the different pairs to remove duplicate points
    for i in range(len(q)):
        q[i] = sorted(list(set(q[i])))

    # Removing the duplicate points
    for i in range(1, len(q)):
        if q[i - 1][0] == q[i][0]:
            if len(q[i]) > len(q[i - 1]):
                q[i - 1] = None
    # Output here will be list of samples which are the starting and end of the high notch

    # Removing the irrelevant values
    q = [q[i] for i in range(len(q)) if q[i] is not None]

    # Plotting the segment start and end points
    return q, z1
