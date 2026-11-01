import React from 'react';
import { render } from '@testing-library/react';
import { getLoadColor, ResourceLoad, hasResourceWarning } from './Footer';

test.each([
 [0, '#00c853'], [25, '#00c853'], [26, '#b2ff59'], [49, '#b2ff59'],
 [50, '#ffeb3b'], [70, '#ffeb3b'], [71, '#ff9800'], [90, '#ff9800'],
 [91, '#ff5252'], [98, '#ff5252'], [99, '#ce93d8'], [100, '#ce93d8'],
 [25.6, '#b2ff59'], [98.6, '#ce93d8'],
])('load %s receives the color of its displayed percentage', (value, color) => {
 expect(getLoadColor(value)).toBe(color);
});
test('footer separates CPU, I/O wait and memory with vertical bars and colors the values', () => {
 const { container } = render(<ResourceLoad system={{ cpu_used: 12, cpu_iowait: 75, mem_used: 99 }} />);
 expect(container.textContent).toBe('12% CPU | 75% I/O-Wait | 99% MEM');
 expect([...container.querySelectorAll('span')].map(s => s.style.color)).toEqual(['rgb(0, 200, 83)', 'rgb(255, 152, 0)', 'rgb(206, 147, 216)']);
});
test.each(['cpu_used', 'cpu_iowait', 'mem_used'])('%s triggers warning at 75 percent', key => {
 expect(hasResourceWarning({ [key]: 74.99 }, {})).toBe(false);
 expect(hasResourceWarning({ [key]: 75 }, {})).toBe(true);
});
test('existing storage and network warnings remain enabled', () => {
 for (const key of ['memfs_used', 'disk_used', 'net_used']) expect(hasResourceWarning({}, { [key]: 75 })).toBe(true);
});
