import pandas as pd
import os
import matplotlib.pyplot as plt
import numpy as np
import statistics

def load_data(filepath, index_col='Date'):
    data = pd.read_excel(filepath)
    data[index_col] = pd.to_datetime(data[index_col])
    data = data.set_index(index_col).to_period('M').to_timestamp('M')
    return data.ffill()

def create_signal(data, window, center=False):
    percentile_40th = lambda n: np.percentile(n, 40)
    temp = data.rolling(window, center=center).apply(percentile_40th).fillna(method='ffill' if center else 'bfill')
    signal = np.where(data > temp, 1, 0)
    signal = np.where(data <= 0.5, 0, signal)
    return pd.DataFrame(signal, columns=['Signal'], index=data.index)

userid = os.getlogin()
datapath = os.path.join('/Users/emaleejimenez/Desktop')

tsry_data = load_data(os.path.join(datapath, 'TsyData.xlsx'))
fed_data = load_data(os.path.join(datapath, 'FEDFUNDS.xls'))

median = statistics.median(fed_data['FEDFUNDS'])
signal_1 = (fed_data > median).astype(int).rename(columns={'FEDFUNDS': 'Signal'})

window = 12 * 5  # 5-Year Rolling window
signal_2 = create_signal(fed_data, window)
signal_3 = create_signal(fed_data, window, center=True)

total_signals = (signal_1 + signal_2 + signal_3).squeeze()
merged_data = pd.concat([total_signals, tsry_data], axis=1, join='inner').rename(columns={0: 'Signal'})

color_dict = {0: 'none', 1: '#FFCCCC', 2: '#FF9999', 3: '#FF6666'}
color_list = merged_data['Signal'].map(color_dict)

fig, ax = plt.subplots(figsize=(18, 10), dpi=300)
merged_data['Rate'].plot(ax=ax, color='blue', label='3-Month Tbill')
proxy = plt.Rectangle((0, 0), 1, 1, fc="#FF6666", label='Higher Rate Regimes')
ax.add_patch(proxy)
for start, end, color in zip(merged_data.index[:-1], merged_data.index[1:], color_list[:-1]):
    ax.fill_between([start, end], merged_data['Rate'].min(), merged_data['Rate'].max(), color=color)
ax.set_title('Interest Rate Regimes')
ax.set_xlabel('Date')
ax.set_ylabel('%')
ax.legend()
plt.show()

total_signals = pd.concat([signal_1, signal_2, signal_3, total_signals], axis=1)
total_signals.columns = ['Signal 1', 'Signal 2', 'Signal 3', 'Total']
model_stats = {'signals': total_signals, 'performance': [signal_3]}
