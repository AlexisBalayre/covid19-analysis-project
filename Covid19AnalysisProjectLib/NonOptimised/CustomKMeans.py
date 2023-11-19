import numpy as np
from numpy.linalg import norm


class CustomKMeans:
    """
    Custom implementation of KMeans algorithm
        Parameters:
            n_clusters (int): Number of clusters
            max_iter (int): Maximum number of iterations
            seed (int): Seed
            tol (float): Tolerance for convergence
            verbose (bool): Print statements

        Attributes:
            n_clusters (int): Number of clusters
            max_iter (int): Maximum number of iterations
            seed (int): Seed
            tol (float): Tolerance for convergence
            verbose (bool): Print statements
            centroids (ndarray): Centroids of the clusters
            iterations (int): Number of iterations taken to converge
            error (float): Sum of squared errors
    """

    def __init__(self, n_clusters, max_iter=20, seed=None, tol=1e-4, verbose=False):
        self.n_clusters = n_clusters  # number of clusters
        self.max_iter = max_iter  # maximum number of iterations
        self.seed = seed  # seed
        self.tol = tol  # tolerance for convergence
        self.verbose = verbose  # print statements

    def __initialise_centroids(self, X):
        """
        Initialise the centroids by choosing random data points

            Parameters:
                X (ndarray): Data points
            Returns:
                (ndarray): Centroids
        """
        rng = np.random.RandomState(self.seed)
        random_idx = rng.permutation(X.shape[0])
        centroids = X[random_idx[: self.n_clusters]]
        return centroids

    def __compute_centroids(self, X, labels):
        """
        Compute the centroids.

            Parameters:
                X (ndarray): Data points
                labels (ndarray): Labels

            Returns:
                (ndarray): Centroids
        """
        centroids = np.zeros((self.n_clusters, X.shape[1]))
        for k in range(self.n_clusters):
            if np.any(labels == k):
                centroids[k, :] = np.mean(X[labels == k, :], axis=0)
            else:
                # Handle empty cluster by reinitialising to a random data point
                centroids[k, :] = X[np.random.randint(X.shape[0]), :]
        return centroids

    def __compute_distance(self, X, centroids):
        """
        Compute the distance between each data point and each centroid.

            Parameters:
                X (ndarray): Data points
                centroids (ndarray): Centroids

            Returns:
                (ndarray): Distance between each data point and each centroid
        """
        distance = np.zeros((X.shape[0], self.n_clusters))
        for k in range(self.n_clusters):
            row_norm = norm(X - centroids[k, :], axis=1)
            distance[:, k] = np.square(row_norm)
        return distance

    def __find_closest_cluster(self, distance):
        """
        Find the closest cluster for each data point.

            Parameters:
                distance (ndarray): Distance between each data point and each centroid

            Returns:
                (ndarray): Closest cluster for each data point
        """
        return np.argmin(distance, axis=1)

    def __compute_sse(self, X, labels, centroids):
        """
        Compute the sum of squared errors.

            Parameters:
                X (ndarray): Data points
                labels (ndarray): Labels
                centroids (ndarray): Centroids

            Returns:
                (float): Sum of squared errors
        """
        distance = np.zeros(X.shape[0])
        for k in range(self.n_clusters):
            distance[labels == k] = norm(X[labels == k] - centroids[k], axis=1)
        return np.sum(np.square(distance))

    def fit(self, X):
        """
        Fit the data points to the model.

                Parameters:
                    X (ndarray): Data points
        """
        self.centroids = self.__initialise_centroids(X)
        for i in range(self.max_iter):
            old_centroids = self.centroids
            distance = self.__compute_distance(X, old_centroids)
            self.labels = self.__find_closest_cluster(distance)
            self.centroids = self.__compute_centroids(X, self.labels)
            # Check for convergence with the given tolerance level
            if np.all(np.abs(old_centroids - self.centroids) <= self.tol):
                if self.verbose:
                    print(f"Convergence reached in {i} iterations")
                break
        self.iterations = i
        self.error = self.__compute_sse(X, self.labels, self.centroids)

    def predict(self, X):
        """
        Predict the closest cluster for each data point.

            Parameters:
                X (ndarray): Data points

            Returns:
                (ndarray): Closest cluster for each data point
        """
        distance = self.__compute_distance(X, self.centroids)
        return self.__find_closest_cluster(distance)
