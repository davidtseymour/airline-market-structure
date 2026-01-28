import sqlite3

from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

from statsmodels.regression.linear_model import WLS, OLS

import matplotlib.pyplot as plt
from sklearn.neighbors import KernelDensity

from cycler import cycler




monochrome = (cycler('color', ['k']) * cycler('marker', ['', '.']) *
              cycler('linestyle', [':', '--', '-.', '-']))
plt.rc('axes', prop_cycle=monochrome)



DB_PATH = "delaydata.db"


def load_airport_data(db_path: str = DB_PATH) -> pd.DataFrame:
    """
    Load airport-airline market data and merge in airport-level market info.

    Returns
    -------
    pd.DataFrame
        airport_airline_market_info joined with selected fields from airport_market_info,
        plus one-hot columns for AirlineHubSize.
    """
    airport_airline_sql = """
        SELECT
            OriginAirportID,
            Year,
            Month,
            MarketShare,
            HubSize,
            MonthlyFlights
        FROM airport_airline_market_info
    """

    airport_market_sql = """
        SELECT
            OriginAirportID,
            Year,
            Month,
            HHI,
            HubSize
        FROM airport_market_info
    """

    # Context manager ensures the connection closes even if a read fails.
    with sqlite3.connect(db_path) as conn:
        airport_airline_market = pd.read_sql_query(airport_airline_sql, conn)
        airport_market = pd.read_sql_query(airport_market_sql, conn)

    # Disambiguate HubSize fields before merging
    airport_airline_market = airport_airline_market.rename(columns={"HubSize": "AirlineHubSize"})
    airport_market = airport_market.rename(columns={"HubSize": "AirportHubSize"})

    merged = airport_airline_market.merge(
        airport_market[["OriginAirportID", "Year", "Month", "HHI", "AirportHubSize"]],
        on=["OriginAirportID", "Year", "Month"],
        how="left",
        validate="m:1",  # many airline-market rows -> one airport-market row per key
    )

    # One-hot encode AirlineHubSize. Prefix avoids collisions with existing column names.
    hub_dummies = pd.get_dummies(merged["AirlineHubSize"], prefix="AirlineHubSize", dtype=int)

    return pd.concat([merged, hub_dummies], axis=1)


def basic_random_sample(
    coef_path: str | Path,
    cov_path: str | Path,
    num_sims: int = 1000,
    seed: int | None = 12345,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Draw random samples of (hhiorigin + hhidest) using a multivariate normal approximation.

    Point estimates are deterministic. Simulation is used only for variance characterization.
    The combined effect is replicated across four hub sizes.
    """
    # Fixed assumptions for this paper
    reg_vars: Sequence[str] = ("hhiorigin", "hhidest")
    n_hub_sizes: int = 4

    if num_sims <= 0:
        raise ValueError("num_sims must be positive.")

    # --- Read coefficient estimates ---
    coef_df = pd.read_csv(coef_path)
    missing = [v for v in reg_vars if v not in coef_df.columns]
    if missing:
        raise KeyError(f"Missing coefficient columns in {coef_path}: {missing}")

    mu = coef_df.loc[0, list(reg_vars)].to_numpy(dtype=float)  # shape (2,)

    # --- Read variance–covariance matrix ---
    cov_df = pd.read_csv(cov_path).set_index("Unnamed: 0")
    Sigma = cov_df.loc[list(reg_vars), list(reg_vars)].to_numpy(dtype=float)  # shape (2,2)

    # --- RNG / sampling ---
    rng = np.random.default_rng(seed)
    draws = rng.multivariate_normal(mu, Sigma, size=num_sims, method="svd")

    # Combine origin + destination effects
    combined = draws.sum(axis=1)  # shape (num_sims,)

    # Replicate across the four hub sizes
    random_sample = np.repeat(combined[:, None], repeats=n_hub_sizes, axis=1)

    # Deterministic point estimate replicated
    true_params = np.repeat(mu.sum(), repeats=n_hub_sizes)

    return random_sample, true_params




def hub_random_sample(
    coef_path: str | Path,
    cov_path: str | Path,
    num_sims: int = 1000,
    seed: int | None = 12345,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Random draws for hub-decomposed concentration effects using MVN approximation.

    Coefficients assumed in this order:
      origin: nonhub, smallhub, mediumhub, largehub
      dest:   nonhub, smallhub, mediumhub, largehub

    Returns
    -------
    random_sample : (num_sims, 4)
        Draws of (origin + dest) effects for each hub size.
    true_params : (4,)
        Point estimates of (origin + dest) effects for each hub size.
    """
    if num_sims <= 0:
        raise ValueError("num_sims must be positive.")

    reg_vars = [
        "nonhubairlineconcorigin",
        "smallhubairlineconcorigin",
        "mediumhubairlineconcorigin",
        "largehubairlineconcorigin",
        "nonhubairlineconcdest",
        "smallhubairlineconcdest",
        "mediumhubairlineconcdest",
        "largehubairlineconcdest",
    ]

    coef_df = pd.read_csv(coef_path)
    missing = [v for v in reg_vars if v not in coef_df.columns]
    if missing:
        raise KeyError(f"Missing coefficient columns in {coef_path}: {missing}")

    mu = coef_df.loc[0, reg_vars].to_numpy(dtype=float)  # (8,)

    cov_df = pd.read_csv(cov_path).set_index("Unnamed: 0")
    Sigma = cov_df.loc[reg_vars, reg_vars].to_numpy(dtype=float)  # (8, 8)

    rng = np.random.default_rng(seed)
    draws = rng.multivariate_normal(mu, Sigma, size=num_sims, method="cholesky")  # (num_sims, 8)

    random_sample = draws[:, :4] + draws[:, 4:]  # (num_sims, 4)
    true_params = mu[:4] + mu[4:]                # (4,)

    return random_sample, true_params



HUB_DUMMY_COLS = ["airline_hub_bin_0", "airline_hub_bin_1", "airline_hub_bin_2", "airline_hub_bin_3"]
GROUP_KEYS = ["OriginAirportID", "Year", "Month"]

def determine_effect_coeff(df_inputs: pd.DataFrame, random_sample: np.ndarray):
    """
    Compute simulated externality components for each airline observation within each airport-month market.

    Args:
        df_inputs: DataFrame with columns:
            - OriginAirportID, Year, Month
            - MarketShare, HHI, MonthlyFlights, AirportHubSize
            - hub dummies in HUB_DUMMY_COLS (one-hot for AirlineHubSize bins)
        random_sample: array of shape (num_sims, 4) of coefficient draws

    Returns:
        monthly_flights: (N,) array
        market_share:    (N,) array
        airport_hub_size:(N,) array
        effect:          (N, num_sims) array  (or (N, 4) depending on your random_sample)
        origin_airport_id:(N,) array
    """
    if random_sample.ndim != 2 or random_sample.shape[1] != 4:
        raise ValueError(f"random_sample must have shape (num_sims, 4). Got {random_sample.shape}")

    missing = set(GROUP_KEYS + ["MarketShare", "HHI", "MonthlyFlights", "AirportHubSize"]) - set(df_inputs.columns)
    missing |= set(HUB_DUMMY_COLS) - set(df_inputs.columns)
    if missing:
        raise ValueError(f"df_inputs missing columns: {sorted(missing)}")

    effect_list = []
    monthly_flights = []
    market_share = []
    airport_hub_size = []
    origin_airport_id = []

    for _, group in df_inputs.groupby(GROUP_KEYS):
        if len(group) <= 1:
            continue

        # Precompute totals S_total_by_bin = sum_j s_j * I_jbin
        s = group["MarketShare"].to_numpy()
        I = group[HUB_DUMMY_COLS].to_numpy().astype(float)  # (n_airlines, 4)
        S_total_by_bin = (s[:, None] * I).sum(axis=0)       # (4,)

        hhi = group["HHI"].to_numpy()
        comp_1 = 2.0 * (s - hhi)  # (n_airlines,)

        # For each airline i: others vector = S_total_by_bin - s_i * I_i
        others_by_bin = S_total_by_bin[None, :] - (s[:, None] * I)  # (n_airlines, 4)

        # comp_2_i = random_sample @ others_by_bin_i
        # random_sample: (num_sims,4), others_by_bin_i: (4,) => (num_sims,)
        # vectorize across i by transposing:
        comp_2 = (random_sample @ others_by_bin.T).T  # (n_airlines, num_sims)

        effect_mat = comp_1[:, None] * comp_2          # (n_airlines, num_sims)

        monthly_flights.append(group["MonthlyFlights"].to_numpy())
        market_share.append(s)
        airport_hub_size.append(group["AirportHubSize"].to_numpy())
        origin_airport_id.append(group["OriginAirportID"].to_numpy())
        effect_list.append(effect_mat)

    if not effect_list:
        # no markets with >1 airline
        return (np.array([]), np.array([]), np.array([]), np.empty((0, random_sample.shape[0])), np.array([]))

    monthly_flights = np.concatenate(monthly_flights)
    market_share = np.concatenate(market_share)
    airport_hub_size = np.concatenate(airport_hub_size)
    origin_airport_id = np.concatenate(origin_airport_id)
    effect = np.vstack(effect_list)

    return monthly_flights, market_share, airport_hub_size, effect, origin_airport_id


def determine_effect_coeff(
    df_inputs: pd.DataFrame,
    random_sample: np.ndarray,
    group_keys: list[str] | tuple[str, ...] = ("OriginAirportID", "Year", "Month"),
    hub_dummy_cols: list[str] | tuple[str, ...] = (
        "AirlineHubSize_0",
        "AirlineHubSize_1",
        "AirlineHubSize_2",
        "AirlineHubSize_3",
    ),
):
    """
    Compute simulated externality components for each airline observation within each market.

    Args:
        df_inputs: must contain group_keys + MarketShare, HHI, MonthlyFlights, AirportHubSize + hub_dummy_cols
        random_sample: shape (num_sims, 4) coefficient draws
        group_keys: columns defining a market (e.g., airport-month)
        hub_dummy_cols: one-hot columns for airline hub bins (length 4)

    Returns:
        monthly_flights: (N,) array
        market_share: (N,) array
        airport_hub_size: (N,) array
        effect: (N, num_sims) array
        origin_airport_id: (N,) array (first element of group_keys by default; see note)
    """
    if random_sample.ndim != 2 or random_sample.shape[1] != len(hub_dummy_cols):
        raise ValueError(
            f"random_sample must have shape (num_sims, {len(hub_dummy_cols)}). Got {random_sample.shape}"
        )

    required = set(group_keys) | {"MarketShare", "HHI", "MonthlyFlights", "AirportHubSize"} | set(hub_dummy_cols)
    missing = required - set(df_inputs.columns)
    if missing:
        raise ValueError(f"df_inputs missing columns: {sorted(missing)}")

    effect_list = []
    monthly_flights = []
    market_share = []
    airport_hub_size = []
    group_id_first_key = []  # keeps the first key value for each row; adjust if you want a different id

    for _, group in df_inputs.groupby(list(group_keys)):
        if len(group) <= 1:
            continue

        s = group["MarketShare"].to_numpy()
        I = group[list(hub_dummy_cols)].to_numpy().astype(float)   # (n_airlines, 4)
        S_total_by_bin = (s[:, None] * I).sum(axis=0)              # (4,)

        hhi = group["HHI"].to_numpy()
        comp_1 = 2.0 * (s - hhi)                                   # (n_airlines,)

        others_by_bin = S_total_by_bin[None, :] - (s[:, None] * I) # (n_airlines, 4)

        comp_2 = (random_sample @ others_by_bin.T).T               # (n_airlines, num_sims)
        effect_mat = comp_1[:, None] * comp_2                      # (n_airlines, num_sims)

        monthly_flights.append(group["MonthlyFlights"].to_numpy())
        market_share.append(s)
        airport_hub_size.append(group["AirportHubSize"].to_numpy())
        group_id_first_key.append(group[group_keys[0]].to_numpy())
        effect_list.append(effect_mat)

    if not effect_list:
        return (
            np.array([]),
            np.array([]),
            np.array([]),
            np.empty((0, random_sample.shape[0])),
            np.array([]),
        )

    return (
        np.concatenate(monthly_flights),
        np.concatenate(market_share),
        np.concatenate(airport_hub_size),
        np.vstack(effect_list),
        np.concatenate(group_id_first_key),
    )



def find_slopes(
    market_share,
    hub_size,
    effect,
    weights=None,  # None or array-like length N
):
    """
    Estimate hub-specific linear approximations of simulated effects.

    For each hub-size category (0–3), and for each column of `effect`, estimate:
        effect_{i,s} = α_{h,s} + β_{h,s} · market_share_i
    using OLS if `weights` is None, or WLS with hub-sliced weights otherwise.

    Parameters
    ----------
    market_share:
        Array-like of shape (N,). Market share for each observation.
    hub_size:
        Array-like of shape (N,). Hub-size category coded as integers {0,1,2,3}.
    effect:
        Array-like of shape (N, S). Simulated effects; each column is one simulation draw.
    weights:
        Optional array-like of shape (N,). Observation weights. If provided, weights are
        sliced by hub and used in WLS. If None, regressions are unweighted.

    Returns
    -------
    slope_mat:
        List of length 4. Each element is a numpy array of shape (S,) containing slope
        estimates β_{h,s} for hub h across simulations.
    intercept_mat:
        List of length 4. Each element is a numpy array of shape (S,) containing intercept
        estimates α_{h,s} for hub h across simulations.
    summary_list:
        Dict keyed by hub-size category (0–3). Each value contains summary statistics
        (mean, median, 2.5th and 97.5th percentiles) for slopes and intercepts across
        simulations, plus the number of observations used for that hub.
    """
    slope_mat = []
    intercept_mat = []
    summary_list = {}

    market_share = np.asarray(market_share).ravel()
    hub_size = np.asarray(hub_size).ravel()
    effect = np.asarray(effect)

    if market_share.shape[0] != hub_size.shape[0] or market_share.shape[0] != effect.shape[0]:
        raise ValueError("market_share, hub_size, and effect must align on the first dimension (N).")

    if weights is not None:
        weights = np.asarray(weights).ravel()
        if weights.shape[0] != hub_size.shape[0]:
            raise ValueError("weights must have the same length as hub_size.")

    _, columns = effect.shape

    for hub in range(4):
        hub_ind = (hub_size == hub)
        n_obs = int(hub_ind.sum())

        slope_vec = []
        intercept_vec = []

        ms_hub = market_share[hub_ind].reshape(-1, 1)
        X = np.concatenate([np.ones_like(ms_hub), ms_hub], axis=1)

        if weights is None:
            w_hub = None
        else:
            w_hub = weights[hub_ind]
            if np.any(w_hub <= 0):
                raise ValueError(f"Non-positive weights found for hub {hub}.")

        for column in range(columns):
            effect_hub = effect[hub_ind, column].reshape(-1, 1)

            if w_hub is None:
                results = OLS(effect_hub, X).fit()
            else:
                results = WLS(effect_hub, X, weights=w_hub).fit()

            reg_int, reg_slope = results.params
            slope_vec.append(reg_slope)
            intercept_vec.append(reg_int)

        slope_vec = np.asarray(slope_vec, dtype=float)
        intercept_vec = np.asarray(intercept_vec, dtype=float)

        slope_mat.append(slope_vec)
        intercept_mat.append(intercept_vec)

        summary_list[int(hub)] = {
            "n_obs": n_obs,
            "intercept": {
                "median": float(np.percentile(intercept_vec, 50)),
                "mean": float(intercept_vec.mean()),
                "p2_5": float(np.percentile(intercept_vec, 2.5)),
                "p97_5": float(np.percentile(intercept_vec, 97.5)),
            },
            "slope": {
                "median": float(np.percentile(slope_vec, 50)),
                "mean": float(slope_vec.mean()),
                "p2_5": float(np.percentile(slope_vec, 2.5)),
                "p97_5": float(np.percentile(slope_vec, 97.5)),
            },
        }

    return slope_mat, intercept_mat, summary_list

def prob_values_different(
    slopes,
    labels = None,
    include_diagonal = False,
):
    """
    Pairwise probability that slope i > slope j across simulation draws.

    Parameters
    ----------
    slopes
        Either:
        - list/tuple of length K, each element shape (num_sims,) or (num_sims, 1), or
        - array of shape (num_sims, K).
        Values are assumed to be simulation draws for each slope.
    labels
        Optional labels of length K for rows/columns (e.g., ["Nonhub","Small","Med","Large"]).
        Defaults to range(K).
    include_diagonal
        If False (default), diagonal entries are NaN. If True, diagonal entries are 0.5.

    Returns
    -------
    pd.DataFrame
        K x K matrix where entry (i, j) is P(slope_i > slope_j).
    """
    # Normalize input to shape (num_sims, K)
    if isinstance(slopes, np.ndarray):
        arr = slopes
        if arr.ndim != 2:
            raise ValueError(f"`slopes` array must be 2D (num_sims, K). Got shape {arr.shape}.")
    else:
        cols = []
        for k, s in enumerate(slopes):
            s = np.asarray(s).reshape(-1)
            cols.append(s)
        arr = np.column_stack(cols)

    num_sims, k = arr.shape

    if labels is None:
        labels = list(range(k))
    if len(labels) != k:
        raise ValueError(f"`labels` must have length K={k}. Got {len(labels)}.")

    # Pairwise probabilities: P(i > j)
    # (num_sims, K, 1) > (num_sims, 1, K) -> (num_sims, K, K)
    probs = (arr[:, :, None] > arr[:, None, :]).mean(axis=0)

    df = pd.DataFrame(probs, index=labels, columns=labels)

    if include_diagonal:
        np.fill_diagonal(df.values, 0.5)
    else:
        np.fill_diagonal(df.values, np.nan)

    return df



def plot_market_share_kde_by_hub(
    market_share: np.ndarray,
    hub_size: np.ndarray,
    *,
    bandwidth: float = 0.05,
    n_grid: int = 1000,
    x_min: float | None = 0.0,
    x_max: float | None = 1.0,
    hub_labels: dict[int, str] | None = None,
    fig_size: tuple[int, int] = (12, 5),
    show: bool = True,
):
    """
    Plot boundary-corrected KDEs of market share by hub-size group.

    For each hub group, this plots:
      (1) KDE of market share with reflection at 0 and 1 (boundary correction)
      (2) "market-share weighted" density: x * f(x), normalized to integrate to 1 on the grid.

    Returns
    -------
    fig, (ax1, ax2)
    """
    market_share = np.asarray(market_share).ravel()
    hub_size = np.asarray(hub_size).ravel()

    if market_share.shape[0] != hub_size.shape[0]:
        raise ValueError("market_share and hub_size must have the same length")

    hub_size_unique = np.unique(hub_size)

    default_labels = {0: "Non", 1: "Small", 2: "Medium", 3: "Large"}
    labels = dict(default_labels)
    if hub_labels is not None:
        labels.update(hub_labels)  # overrides defaults where provided

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=fig_size)

    for hub in hub_size_unique:
        hub_ind = (hub_size == hub)
        data = market_share[hub_ind]
        if data.size == 0:
            continue

        data_2d = data[:, np.newaxis]
        kde = KernelDensity(kernel="gaussian", bandwidth=bandwidth).fit(data_2d)

        xmin = float(np.min(data)) if x_min is None else float(x_min)
        xmax = float(np.max(data)) if x_max is None else float(x_max)
        if xmin == xmax:
            eps = 1e-6
            xmin -= eps
            xmax += eps

        x_values = np.linspace(xmin, xmax, n_grid)[:, np.newaxis]

        log_density = kde.score_samples(x_values)
        density = np.exp(log_density)

        left_reflection = -x_values          # reflect around 0
        right_reflection = 2 - x_values      # reflect around 1

        density += np.exp(kde.score_samples(left_reflection))
        density += np.exp(kde.score_samples(right_reflection))

        label = labels.get(int(hub), f"Hub {hub}")

        ax1.plot(x_values[:, 0], density, label=label)

        dx = float(x_values[1, 0] - x_values[0, 0])
        weighted_density = x_values[:, 0] * density
        area = float(np.sum(weighted_density) * dx)
        if area > 0:
            weighted_density = weighted_density / area

        ax2.plot(x_values[:, 0], weighted_density, label=label)

    for ax in (ax1, ax2):
        ax.set_xlabel("Market share")
        ax.set_ylabel("Density")

    ax1.set_title("Market share kernel density estimation")
    ax2.set_title("Market share kernel density estimation - market share weighted")
    ax2.legend()

    if show:
        plt.show()

    return fig, (ax1, ax2)




def determine_effect_coeff_true(true_params, airport_airline_market):
    """
    Compute the market-structure externality effect at the airline–airport–month level
    using observed data and deterministic coefficient values.

    For each airport–year–month market with more than one airline, this function:
      1. Computes the marginal effect component:
         2 * (MarketShare_i − HHI_market)
      2. Computes the contribution of *other airlines* in the market by hub size:
         sum_{j ≠ i} MarketShare_j × 1{AirlineHubSize_j = h}
      3. Applies the hub-size–specific coefficients to obtain the total external effect.

    This implementation avoids repeated DataFrame slicing by precomputing
    hub-size-weighted market share totals at the group level and subtracting
    each airline’s own contribution.

    Parameters
    ----------
    true_params : array-like, shape (4,)
        Deterministic coefficient vector corresponding to airline hub sizes
        [non-hub, small hub, medium hub, large hub].

    airport_airline_market : pandas.DataFrame
        Flight-level or airline-level market data. Must contain:
        - MarketShare
        - HHI
        - MonthlyFlights
        - AirportHubSize
        - AirlineHubSize
        - OriginAirportID
        - Year, Month
        - AirlineHubSize_0 ... AirlineHubSize_3 (one-hot indicators)

    Returns
    -------
    pandas.DataFrame
        DataFrame with one row per airline–airport–month observation, containing:
        - monthly flights
        - market share
        - airport hub size
        - airline hub size
        - hhi
        - num airlines
        - airport id
        - effect (scalar externality measure)
    """
    true_params = np.asarray(true_params).reshape(-1)
    if true_params.shape != (4,):
        raise ValueError("true_params must be a length-4 vector")

    hub_cols = [
        "AirlineHubSize_0",
        "AirlineHubSize_1",
        "AirlineHubSize_2",
        "AirlineHubSize_3",
    ]

    results = []

    # Group by airport–year–month markets
    grouped = airport_airline_market.groupby(
        ["OriginAirportID", "Year", "Month"], sort=False
    )

    for (_, group) in grouped:
        num_airlines = len(group)
        if num_airlines <= 1:
            continue

        # Total hub-size-weighted market shares across all airlines in the market
        total_hub_market_share = (
            group[hub_cols]
            .multiply(group["MarketShare"], axis=0)
            .sum()
            .to_numpy(dtype=float)
        )

        for _, row in group.iterrows():
            # Marginal concentration component
            comp_1 = 2.0 * (row["MarketShare"] - row["HHI"])

            # Remove the airline's own contribution from hub totals
            own_hub_vector = row[hub_cols].to_numpy(dtype=float)
            other_airlines_market_share = (
                total_hub_market_share
                - row["MarketShare"] * own_hub_vector
            )

            # Apply hub-size coefficients
            comp_2 = float(true_params @ other_airlines_market_share)

            effect = comp_1 * comp_2

            results.append({
                "monthly flights": row["MonthlyFlights"],
                "market share": row["MarketShare"],
                "airport hub size": row["AirportHubSize"],
                "airline hub size": row["AirlineHubSize"],
                "hhi": row["HHI"],
                "num airlines": num_airlines,
                "airport id": row["OriginAirportID"],
                "effect": effect,
            })

    return pd.DataFrame(results)



def plot_true_externality(
    effect_df: pd.DataFrame,
    *,
    seed: int = 42,
    n_scatter: int = 1000,
    size_marker: int = 10,
    ylim: tuple[float, float] = (-9, 2),
    xlim: tuple[float, float] = (-0.05, 1.05),
    save_plots: bool = True,
    out_prefix: str = "externality_hub_",
    out_format: str = "eps",
    use_weights: str = "ms",   # "ms", "flights", or "ms_x_flights"
) -> pd.DataFrame:
    """
    Fit and plot the 'true' externality relationship by airport hub size.

    For each airport hub-size group (coded 0..3), this function:
      - Runs a weighted least squares regression: effect ~ 1 + market_share
      - Stores the fitted intercept and slope
      - Produces a scatter plot of (market share, effect) using a weighted sample

    Parameters
    ----------
    effect_df
        DataFrame containing at least the columns:
        ['airport hub size', 'effect', 'market share', 'monthly flights'].
    seed
        Random seed for reproducible subsampling in the scatter plots.
    n_scatter
        Number of points to sample for the scatter plot within each hub group.
    size_marker
        Marker size for the scatter plot.
    ylim, xlim
        Plot axis limits.
    save_plots
        Whether to save plots to disk.
    out_prefix
        Prefix for saved plot filenames (hub code appended).
    out_format
        File format for saved plots (e.g., 'eps', 'png', 'pdf').
    use_weights
        Which weights to use in WLS and in sampling:
        - "ms": market-share weights
        - "flights": monthly flights weights
        - "ms_x_flights": product of market share and flights

    Returns
    -------
    pd.DataFrame
        DataFrame indexed by hub description with columns ['intercept', 'slope'].
    """
    hub_desc = ["Non-hub airports", "Small hub airports", "Medium hub airports", "Large hub airports"]

    required = {"airport hub size", "effect", "market share", "monthly flights"}
    missing = required - set(effect_df.columns)
    if missing:
        raise ValueError(f"effect_df is missing required columns: {sorted(missing)}")

    rng = np.random.default_rng(seed=seed)

    slope_vec = []
    intercept_vec = []

    for hub in range(4):
        hub_ind = (effect_df["airport hub size"] == hub)

        effect_hub = effect_df.loc[hub_ind, "effect"].to_numpy()
        ms_hub = effect_df.loc[hub_ind, "market share"].to_numpy()
        flights_hub = effect_df.loc[hub_ind, "monthly flights"].to_numpy()

        # Choose regression + sampling weights
        if use_weights == "ms":
            w = ms_hub
        elif use_weights == "flights":
            w = flights_hub
        elif use_weights == "ms_x_flights":
            w = ms_hub * flights_hub
        else:
            raise ValueError("use_weights must be one of: 'ms', 'flights', 'ms_x_flights'")

        # Basic safety: drop any non-finite or non-positive weights
        ok = np.isfinite(effect_hub) & np.isfinite(ms_hub) & np.isfinite(w) & (w > 0)
        effect_hub = effect_hub[ok]
        ms_hub = ms_hub[ok]
        w = w[ok]

        # Design matrix: [1, market share]
        X = np.column_stack([np.ones_like(ms_hub), ms_hub])

        results = WLS(effect_hub, X, weights=w).fit()
        reg_int, reg_slope = results.params

        intercept_vec.append(reg_int)
        slope_vec.append(reg_slope)

        # Weighted subsample for plotting
        n = len(ms_hub)
        if n == 0:
            continue

        draw = min(n_scatter, n)
        p = w / w.sum()

        # If draw == n, just take everything (no need for random)
        if draw == n:
            idx = np.arange(n)
        else:
            # If draw > n and replace=False would fail, we already capped draw=min(...)
            idx = rng.choice(np.arange(n), size=draw, replace=False, p=p)

        plt.figure(figsize=(4.25, 4))
        ax = plt.subplot(111)
        ax.scatter(ms_hub[idx], effect_hub[idx], c="black", s=size_marker)

        ax.set_ylabel("External cost")
        ax.set_xlabel("Market share")
        ax.set_title(hub_desc[hub])
        ax.set_ylim(list(ylim))
        ax.set_xlim(list(xlim))
        plt.tight_layout()

        if save_plots:
            filename = f"{out_prefix}{hub}.{out_format}"
            plt.savefig(filename, format=out_format)

        plt.show()

    return pd.DataFrame({"intercept": intercept_vec, "slope": slope_vec}, index=hub_desc)

def print_tables(summary_tables) :
    """
    Pretty-print a collection of summary tables grouped by hub size.

    Parameters
    ----------
    summary_tables
        Dictionary mapping hub identifiers to table-like dictionaries.
        Each value must be convertible to a pandas DataFrame
        (e.g., dict-of-lists or dict-of-dicts).

    Notes
    -----
    - Each hub's table is printed separately.
    - Table rows are indented for readability in console output.
    """
    for hub, table in summary_tables.items():
        print(f"Hub size: {hub}")

        df = pd.DataFrame(table)

        # Convert DataFrame to string and indent each row
        table_str = df.to_string()
        indented = "\n".join("    " + line for line in table_str.splitlines())

        print(indented)



def plot_externality_kernel_by_hub(ax, effect_df, *, bandwidth=0.05, n_grid=100,
                                   weight_col="monthly flights",
                                   title=None):
    """
    Plot kernel-smoothed external cost vs market share by airport hub size.

    For each hub-size group (coded 0..3), this computes a Gaussian kernel smoother:
        y_hat(x0) = sum_i K((x_i - x0)/h) * w_i * y_i
                    ----------------------------------
                    sum_i K((x_i - x0)/h) * w_i

    Parameters
    ----------
    ax
        Matplotlib Axes object to plot on.
    effect_df
        DataFrame containing at least:
          - 'airport hub size'
          - 'market share'
          - 'effect'
        If `weight_col` is not None, must also contain that column.
    bandwidth
        Kernel bandwidth.
    n_grid
        Number of grid points used for smoothing.
    weight_col
        Column name used for observation weights (e.g. 'monthly flights').
        If None, equal weights are used.
    title
        Optional title for the axis.

    Returns
    -------
    ax
        The axis that was plotted on.
    """
    hub_labels = [
        "Non hub airports",
        "Small hub airports",
        "Medium hub airports",
        "Large hub airports",
    ]

    for hub in range(4):
        hub_ind = effect_df["airport hub size"] == hub

        x = np.asarray(effect_df.loc[hub_ind, "market share"])
        y = np.asarray(effect_df.loc[hub_ind, "effect"])

        if x.size == 0:
            continue

        if weight_col is None:
            w = np.ones_like(x, dtype=float)
        else:
            w = np.asarray(effect_df.loc[hub_ind, weight_col], dtype=float)

        # Grid for smoothing
        x_smooth = np.linspace(float(x.min()), float(x.max()), n_grid)

        # Gaussian kernel weights
        distances = x[:, None] - x_smooth[None, :]
        K = np.exp(-0.5 * (distances / bandwidth) ** 2)
        W = K * w[:, None]

        denom = W.sum(axis=0)

        # Safe normalization
        y_smooth = np.full_like(x_smooth, np.nan, dtype=float)
        valid = denom > 0
        y_smooth[valid] = (W[:, valid] * y[:, None]).sum(axis=0) / denom[valid]

        ax.plot(x_smooth, y_smooth, label=hub_labels[hub])

    ax.set_xlabel("Market share")
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylabel("External cost")

    if title:
        ax.set_title(title)

    ax.legend()
    return ax

def plot_kernel_density_function_true(effect_1, effect_2, bandwidth=0.05,
                                      save_path="kernel_smoothing.eps"):
    """
    Compare kernel-smoothed external cost functions with and without hub-size interactions.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 4), sharey=True)

    plot_externality_kernel_by_hub(
        ax1,
        effect_1,
        bandwidth=bandwidth,
        title="No hub size interactions",
    )

    plot_externality_kernel_by_hub(
        ax2,
        effect_2,
        bandwidth=bandwidth,
        title="Hub size interactions",
    )

    fig.tight_layout()

    if save_path:
        plt.savefig(save_path, format="eps")

    plt.show()
    return fig, (ax1, ax2)
