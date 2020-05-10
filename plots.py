#!/usr/bin/env python3

from typing import Sequence

import matplotlib.pyplot as plt

from model import TRIPLE, SPIKE, DECAY, BUMP, Model
from ttime import TimePeriod


def plot_models_range(name: str,
                      base_price: int,
                      models: Sequence[Model],
                      add_points: bool = False) -> None:

    colors = {
        TRIPLE: 'orange',
        SPIKE:  'green',
        DECAY:  'red',
        BUMP:   'purple',
    }

    _fig, ax = plt.subplots()

    # cosmetics
    ax.set_title(f"{name}'s weekly forecast: ")
    ax.set_ylabel('Turnip Price')
    ax.set_xticklabels(['Mon AM', 'Mon PM', 'Tue AM', 'Tue PM', 'Wed AM', 'Wed PM',
                        'Thu AM', 'Thu PM', 'Fri AM', 'Fri PM', 'Sat AM', 'Sat PM'])
    ax.xaxis.set_ticks(range(2, 14))
    plt.xticks(rotation=45)
    plt.grid(axis='both', which='major', ls='dotted')
    ax.set_ylim(0, 660)
    plt.tight_layout()
    plt.hlines(y=base_price, xmin=2, xmax=13, linestyles='dashed')

    if len(models) == 0:
        return

    a_model = models[0]

    continuous_priced_days = []
    continuous_priced_chunk = set()
    continuous_unpriced_days = []
    continuous_unpriced_chunk = set()
    for day in range(2, 14):
        # does this day have data?
        if a_model.timeline[TimePeriod(day)].price.is_atomic:
            # is tomorrow a valid day to have data?
            if day < 13:
                # does tomorrow have data?
                if a_model.timeline[TimePeriod(day + 1)].price.is_atomic:
                    # build onto the chunk
                    continuous_priced_chunk.update([day, day + 1])
                # chunk broken.
                else:
                    continuous_priced_chunk.update([day])
                    continuous_priced_days.append(list(continuous_priced_chunk))
                    continuous_priced_chunk = set()
            else:
                # end of the week, finish the priced_days
                continuous_priced_days.append(list(continuous_priced_chunk))
        # today does not have data
        else:
            # is tomorrow a valid day to have data?
            if day < 13:
                # does it?
                if not a_model.timeline[TimePeriod(day + 1)].price.is_atomic:
                    # build the chunk
                    if day != 2:
                        # add yesterday unless today is monday_am
                        continuous_unpriced_chunk.update([day - 1, day, day + 1])
                    else:
                        continuous_unpriced_chunk.update([day, day + 1])
                # chunk broken
                else:
                    if day != 2:
                        continuous_unpriced_chunk.update([day - 1, day, day + 1])
                    else:
                        continuous_unpriced_chunk.update([day, day + 1])
                    continuous_unpriced_days.append(list(sorted(continuous_unpriced_chunk, key=lambda x: x)))
                    continuous_unpriced_chunk = set()
            else:
                # end of the week, finish the unpriced_days
                continuous_unpriced_days.append(list(continuous_unpriced_chunk))

    for chunk in continuous_priced_days:
        vals = [a_model.timeline[TimePeriod(day)].price.value for day in chunk]
        plt.plot(chunk, vals, c='black', solid_capstyle='round', solid_joinstyle='round')

    for chunk in continuous_unpriced_days:
        if len(chunk) == 1:
            # if this is one day of unpriced data, connect it to the neighbors.
            value = chunk[0]
            chunk = [value - 1, value, value + 1]
        for model in models:
            low_vals = [model.timeline[TimePeriod(day)].price.lower for day in chunk]
            high_vals = [model.timeline[TimePeriod(day)].price.upper for day in chunk]

            alpha = 1 / len(models)

            plt.fill_between(chunk, low_vals, high_vals, alpha=alpha, color=colors[model.model_type])

            if add_points:
                plt.scatter(chunk, low_vals, c='black', s=2)
                plt.scatter(chunk, high_vals, c='black', s=2)


def plot_models_range_interactive(name: str,
                                  base_price: int,
                                  models: Sequence[Model],
                                  add_points: bool = False) -> None:
    '''
    Plot a fill_between for all models' low and high values using an
    alpha (transparency) equal to 1/num_models. Plot a regular line
    for all fixed prices.

    Shows ~probability of various prices based on your possible models.
    '''
    plot_models_range(name, base_price, models,
                      add_points)
    filename = name + ".png"
    plt.savefig(filename, bbox_inches='tight')