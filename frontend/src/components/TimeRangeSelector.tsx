import React from 'react';

interface TimeRangeSelectorProps {
  selectedDays?: number;
  onChange: (days: number | undefined) => void;
}

export const TimeRangeSelector: React.FC<TimeRangeSelectorProps> = ({ selectedDays, onChange }) => {
  return (
    <div className="time-range-group">
      <button
        type="button"
        className={`time-range-btn ${selectedDays === 7 ? 'active' : ''}`}
        onClick={() => onChange(7)}
      >
        7 Days
      </button>
      <button
        type="button"
        className={`time-range-btn ${selectedDays === 30 ? 'active' : ''}`}
        onClick={() => onChange(30)}
      >
        30 Days
      </button>
      <button
        type="button"
        className={`time-range-btn ${selectedDays === undefined ? 'active' : ''}`}
        onClick={() => onChange(undefined)}
      >
        All Time
      </button>
    </div>
  );
};
