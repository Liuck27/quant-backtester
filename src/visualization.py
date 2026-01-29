import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Optional

def plot_equity_curve(equity_df: pd.DataFrame, title: str = "Equity Curve"):
    """
    Plots the equity curve from the dataframe.
    
    Args:
        equity_df (pd.DataFrame): DataFrame with 'equity' column and timestamp index.
        title (str): Plot title.
    """
    if equity_df.empty or 'equity' not in equity_df.columns:
        print("No equity data to plot.")
        return

    plt.figure(figsize=(12, 6))
    plt.plot(equity_df.index, equity_df['equity'], label='Portfolio Equity')
    
    plt.title(title)
    plt.xlabel('Date')
    plt.ylabel('Equity Value')
    plt.legend()
    plt.grid(True)
    plt.show()

def plot_drawdown(drawdown_series: pd.Series, title: str = "Drawdown"):
    """
    Plots the drawdown series as an area chart.
    
    Args:
        drawdown_series (pd.Series): Series of drawdown values (usually negative).
        title (str): Plot title.
    """
    if drawdown_series.empty:
        print("No drawdown data to plot.")
        return

    plt.figure(figsize=(12, 4))
    plt.fill_between(drawdown_series.index, drawdown_series, 0, color='red', alpha=0.3, label='Drawdown')
    plt.plot(drawdown_series.index, drawdown_series, color='red', linewidth=1)
    
    plt.title(title)
    plt.xlabel('Date')
    plt.ylabel('Drawdown (%)')
    plt.legend()
    plt.grid(True)
    plt.show()

def plot_param_heatmap(results_df: pd.DataFrame, x_param: str, y_param: str, metric: str, title: Optional[str] = None):
    """
    Plots a heatmap of a performance metric vs two parameters.
    
    Args:
        results_df (pd.DataFrame): DataFrame containing parameter columns and the metric column.
        x_param (str): Name of column for X-axis parameter.
        y_param (str): Name of column for Y-axis parameter.
        metric (str): Name of column for the metric values (e.g. 'Sharpe Ratio').
        title (str): Plot title.
    """
    if results_df.empty:
        print("No results to plot.")
        return
        
    required_cols = [x_param, y_param, metric]
    if not all(col in results_df.columns for col in required_cols):
        print(f"Missing columns. Required: {required_cols}")
        return

    # Pivot the data for heatmap
    pivot_table = results_df.pivot(index=y_param, columns=x_param, values=metric)
    
    plt.figure(figsize=(10, 8))
    sns.heatmap(pivot_table, annot=True, fmt=".2f", cmap="viridis", cbar_kws={'label': metric})
    
    plt.title(title or f"{metric} Heatmap: {x_param} vs {y_param}")
    plt.xlabel(x_param)
    plt.ylabel(y_param)
    plt.show()
