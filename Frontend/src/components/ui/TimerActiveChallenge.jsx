import React, { useState, useEffect } from 'react';

const TimerActiveChallenge = ({ fetchedData }) => {
  const [timeLeft, setTimeLeft] = useState({ hours: '00', minutes: '00', seconds: '00' });
  const [creationDate, setCreationDate] = useState('');
  const [creationTime, setCreationTime] = useState('');

  useEffect(() => {
    if (!fetchedData?.challenge?.createdAt) {
      console.error("Invalid createdAt value");
      return;
    }

    const createdAt = new Date(fetchedData.challenge.createdAt);
    if (isNaN(createdAt.getTime())) {
      console.error("Invalid date format for createdAt");
      return;
    }

    // Calculate midnight of the same day
    const midnightSameDay = new Date(createdAt);
    midnightSameDay.setHours(24, 0, 0, 0); // Set to midnight (24:00:00)

    const formatDateTime = (date) => {
      // Format date as DD/MM/YYYY
      const day = String(date.getDate()).padStart(2, '0');
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const year = date.getFullYear();
      const formattedDate = `${day}/${month}/${year}`;
      
      // Format time as HH:MM:SS in 24-hour format
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      const seconds = String(date.getSeconds()).padStart(2, '0');
      const formattedTime = `${hours}:${minutes}:${seconds}`;
      
      return { formattedDate, formattedTime };
    };

    const { formattedDate, formattedTime } = formatDateTime(createdAt);
    setCreationDate(formattedDate);
    setCreationTime(formattedTime);

    const calculateTimeLeft = () => {
      const now = new Date();
      const remainingTime = midnightSameDay - now;
      
      if (remainingTime <= 0) {
        setTimeLeft({ hours: '00', minutes: '00', seconds: '00' });
        clearInterval(timer);
        deleteActiveChallenge(fetchedData.challenge.challengeId);
      } else {
        const hours = Math.floor(remainingTime / (1000 * 60 * 60));
        const minutes = Math.floor((remainingTime % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((remainingTime % (1000 * 60)) / 1000);

        setTimeLeft({
          hours: String(hours).padStart(2, '0'),
          minutes: String(minutes).padStart(2, '0'),
          seconds: String(seconds).padStart(2, '0'),
        });
      }
    };

    const timer = setInterval(calculateTimeLeft, 1000);
    calculateTimeLeft(); // Initial call

    return () => clearInterval(timer);
  }, [fetchedData]);

  const deleteActiveChallenge = async (challengeId) => {
    try {
      console.log(`Deleting challenge with ID: ${challengeId} at midnight`);
      // Replace with your actual API call to delete the challenge
      // await axios.delete(`/api/challenges/${challengeId}`);
    } catch (error) {
      console.error('Error deleting challenge:', error);
    }
  };

  return (
    <div className="flex gap-3 items-start w-[225px]">
      <div className="flex gap-6 items-center py-2 pr-8 pl-4 bg-purple-900 min-h-[74px] rounded-[140px] w-[225px] max-md:pr-5">
        <img
          src="https://cdn.builder.io/api/v1/image/assets/TEMP/cff239496af3f485e4fc3d530033b89091c58c13?placeholderIfAbsent=true&apiKey=1455cb398c424e78afe4261a4bb08b71"
          className="object-contain shrink-0 self-stretch my-auto aspect-[0.98] rounded-[1030px] w-[52px]"
          alt="Timer icon"
        />
        <div className="flex flex-col self-stretch my-auto w-[78px]">
          <div className="self-start text-sm leading-loose text-center">Time Left</div>
          <div className="flex gap-1 items-center w-full whitespace-nowrap">
            <div className="self-stretch my-auto text-2xl">
              {timeLeft.hours}:{timeLeft.minutes}:{timeLeft.seconds}
            </div>
            <div className="self-stretch my-auto text-base font-medium leading-none text-center">sec</div>
          </div>
          <div className="text-xs text-gray-300 mt-1">
            Created: {creationDate} at {creationTime}
          </div>
        </div>
      </div>
    </div>
  );
};

export default TimerActiveChallenge;