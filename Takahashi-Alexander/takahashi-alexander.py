# -*- coding: utf-8 -*-
"""
Created on Thu Apr 17 10:26:28 2025

@author: ejimenez

Python Script to re-create the 2002 paper of Takahashi-Alexander Pacing Model
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, FormatStrFormatter

# Dictionary of input parameters
inputs = {
    'expected_call_rate_at_year_x': 0.90,  # % of total calls expected by "year X"
    'expected_call_rate_year': 5,         # The "year X" in which we expect 90% of calls
    'fund_life': 13,                      # Fund lifespan in years
    'expected_return': 0.20,             # Annual expected growth rate (JPM CMA assumption)
    'commitment': 100.0,                  # Total commitment in millions
    'bow_factor': 1.2,                    # Bow factor for distribution ramp shape
    'yield_rate': 0.00                    # Minimum "yield-like" distribution rate
}

class Takahashi_Alexander:
    def __init__(self, inputs):
        
        # Store inputs as instance attributes
        self.expected_call_rate_at_year_x = inputs['expected_call_rate_at_year_x']
        self.expected_call_rate_year = inputs['expected_call_rate_year']
        self.fund_life = inputs['fund_life']
        self.expected_return = inputs['expected_return']
        self.commitment = inputs['commitment']
        self.bow_factor = inputs['bow_factor']
        self.yield_rate = inputs['yield_rate']
        
        # Create an array of years: [0,1,2,...,fund_life]
        self.years = np.arange(self.fund_life + 1)
        
        # Calculate the capital calls right away
        self.calc_cap_calls()

    def calc_cap_calls(self):
        """
        Calculates capital calls for each year using an S-curve approach:
        1) The fraction called by year t is a function of expected_call_rate_at_year_x.
        2) Then we compute the incremental calls each period.
        """
        
        # S-curve for cumulative fraction called at each year
        cumulative_call_rates = 1.0 - (1.0 - self.expected_call_rate_at_year_x) ** (
            self.years / self.expected_call_rate_year
        )
        
        # Optional: a single-year increment as "annual_call_rate" for reference
        annual_call_rate = 1.0 - (1.0 - self.expected_call_rate_at_year_x) ** (
            1.0 / self.expected_call_rate_year
        )
        
        # Build a DataFrame to store results
        capital_call_df = pd.DataFrame({
            'annual_call_rate': annual_call_rate,
            'cumulative_call_rate': cumulative_call_rates
        }, index=self.years)
        capital_call_df.index.name = 'years'
        
        # Compute incremental calls: 
        # difference between this year's cumulative fraction and last year's
        capital_call_df['capital_calls'] = 0.0
        
        capital_call_df.loc[1:, 'capital_calls'] = (
            self.commitment * capital_call_df.loc[1:, 'cumulative_call_rate']
            - self.commitment * capital_call_df.loc[1:, 'cumulative_call_rate'].shift(1, fill_value=0)
        )
        
        # Cumulative calls = running total of incremental
        capital_call_df['cumulative_calls'] = capital_call_df['capital_calls'].cumsum()
        
        # Unfunded portion = total commitment minus calls so far
        capital_call_df['unfunded_commitment'] = (
            self.commitment - capital_call_df['cumulative_calls']
        )
        
        # Store result for use in other methods
        self.capital_call_df = capital_call_df
        
        return capital_call_df

    def calc_distributions(self):
        """
        Calculates fund distributions each year, taking into account a 
        distribution_rate that is the max of (yield_rate, (year/fund_life)^bow_factor).
        Also calculates NAV evolution year by year.
        """
        
        # Start with a DataFrame that references the "principal" as the sum of calls so far.
        capital_distributions_df = pd.DataFrame({
            'principal': self.capital_call_df['cumulative_calls']
        }, index=self.years)
        capital_distributions_df.index.name = 'years'
        
        # For each year, distribution_rate is at least 'yield_rate' 
        # and possibly larger if the bow_factor curve is bigger
        capital_distributions_df['distribution_rate'] = np.where(
            capital_distributions_df.index <= self.fund_life,
            # Take the max of yield_rate or (year/fund_life)^bow_factor
            np.maximum(
                self.yield_rate, 
                (capital_distributions_df.index / self.fund_life) ** self.bow_factor
            ),
            0  # If we exceed fund_life, can set to zero (or some default)
        )

        # Creating NAV and Distribution columns for calculations
        capital_distributions_df['nav'] = 0.0
        capital_distributions_df['distributions'] = 0.0
        
        # Year-by-year loop, since nav[t] depends on nav[t-1] and calls
        for t in range(1, self.fund_life + 1):
            # 1) nav_before = last year's nav grown + capital calls this year
            nav_before = capital_distributions_df.loc[t-1, 'nav'] * (1 + self.expected_return)
            nav_before += self.capital_call_df.loc[t, 'capital_calls']
            
            # 2) distributions = distribution_rate * nav_before
            distr_rate = capital_distributions_df.loc[t, 'distribution_rate']
            distributions = distr_rate * nav_before
            
            # 3) nav_after = nav_before - distributions
            nav_after = nav_before - distributions
            
            # Store results in the row
            capital_distributions_df.loc[t, 'nav'] = nav_after
            capital_distributions_df.loc[t, 'distributions'] = distributions
        
        # Adding cumulative distributions
        capital_distributions_df['cumulative_distributions'] = capital_distributions_df['distributions'].cumsum()
        
        self.capital_distributions_df = capital_distributions_df
        
        self.total_return = (capital_distributions_df['cumulative_distributions'].iloc[-1] - self.commitment) / self.commitment
        
        return capital_distributions_df, total_return
    
    def plot(self):
        fig, ax = plt.subplots(figsize=(8, 5))

        # 1) Plot cumulative calls
        ax.plot(
            self.capital_call_df.index,
            self.capital_call_df['cumulative_calls'],
            label='Called - Cumulative',
            color='tab:blue',
            lw=2
        )
        ax.fill_between(
            self.capital_call_df.index,
            0,
            self.capital_call_df['cumulative_calls'],
            color='tab:blue',
            alpha=0.15
        )

        # 2) Plot cumulative distributions
        ax.plot(
            self.capital_distributions_df.index,
            self.capital_distributions_df['cumulative_distributions'],
            label='Distributed - Cumulative',
            color='tab:orange',
            lw=2
        )
        ax.fill_between(
            self.capital_distributions_df.index,
            0,
            self.capital_distributions_df['cumulative_distributions'],
            color='tab:orange',
            alpha=0.15
        )

        # 3) Plot NAV
        ax.plot(
            self.capital_distributions_df.index,
            self.capital_distributions_df['nav'],
            label='Closing NAV',
            color='tab:green',
            lw=2
        )
        ax.fill_between(
            self.capital_distributions_df.index,
            0,
            self.capital_distributions_df['nav'],
            color='tab:green',
            alpha=0.15
        )

        plt.subplots_adjust(bottom=0.2)

        ax.set_xlabel('Years')
        ax.set_ylabel('$ Millions')
        ax.set_title('Takahashi–Alexander Private Investment Pacing Model')
        ax.legend()

        # Adding the total return text below x-axis
        ax.text(
            0.5, -0.25,
            f"Total Return = {self.total_return * 100:.2f}%",
            transform=ax.transAxes,
            ha='center',
            va='top'
        )

        # Tweak the x-axis to use integer year ticks
        ax.xaxis.set_major_locator(MultipleLocator(1))  # tick every 1 year

        # Format y-axis 
        ax.yaxis.set_major_formatter(FormatStrFormatter('%.0f'))

        # Grid lines
        ax.grid(True, which='major', alpha=0.4)   # major grid

        plt.show()

#%% Run Model

# Call Class and functions
ta_model = Takahashi_Alexander(inputs)
capital_distributions_df = ta_model.calc_distributions()

# plot
ta_model.plot()

# Unpack the data
dist_df, total_return = capital_distributions_df
calls_df = ta_model.capital_call_df
