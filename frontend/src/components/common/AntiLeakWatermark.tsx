import React, { useEffect, useState } from 'react';
import { useAuthStore } from '../../stores/authStore';
import dayjs from 'dayjs';

const AntiLeakWatermark: React.FC = () => {
  const { userInfo } = useAuthStore();
  const [currentTime, setCurrentTime] = useState(dayjs().format('YYYY-MM-DD HH:mm'));

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(dayjs().format('YYYY-MM-DD HH:mm'));
    }, 60000);
    return () => clearInterval(timer);
  }, []);

  if (!userInfo) return null;

  const watermarkText = `${userInfo.full_name} ${userInfo.username} ${userInfo.department_name} ${currentTime}`;
  
  // Create a grid of watermark items
  const items = [];
  for (let i = 0; i < 20; i++) {
    for (let j = 0; j < 10; j++) {
      items.push(
        <div
          key={`${i}-${j}`}
          className="watermark-item"
          style={{
            top: `${i * 150}px`,
            left: `${j * 300}px`,
          }}
        >
          {watermarkText}
        </div>
      );
    }
  }

  return (
    <div className="anti-leak-watermark">
      {items}
    </div>
  );
};

export default AntiLeakWatermark;
