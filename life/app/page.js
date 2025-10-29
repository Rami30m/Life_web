"use client";
import { useState, useEffect } from "react";

import Image from "next/image";
import RegisterPage from "./components/register";
import LoginPage from "./components/login";
import MainPage from "./components/main";
import LoginECPPage from "./components/loginECP"

export default function Home() {
  const [isLogin, setIsLogin] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userData, setUserData] = useState(null);
  const [accessToken, setAccessToken] = useState(null);
  const [refreshToken, setRefreshToken] = useState(null);

  // Загрузка данных из localStorage при монтировании компонента
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const savedAccessToken = localStorage.getItem('accessToken');
      const savedRefreshToken = localStorage.getItem('refreshToken');
      const savedUserData = localStorage.getItem('userData');
      
      if (savedAccessToken && savedRefreshToken && savedUserData) {
        setAccessToken(savedAccessToken);
        setRefreshToken(savedRefreshToken);
        setUserData(JSON.parse(savedUserData));
        setIsAuthenticated(true);
      }
    }
  }, []);

  const handleSuccessfulAuth = (user, tokens) => {
    setUserData(user);
    setAccessToken(tokens.access_token);
    setRefreshToken(tokens.refresh_token);
    setIsAuthenticated(true);
    
    // Сохраняем токены в localStorage
    if (typeof window !== 'undefined') {
      localStorage.setItem('accessToken', tokens.access_token);
      localStorage.setItem('refreshToken', tokens.refresh_token);
      localStorage.setItem('userData', JSON.stringify(user));
    }
  };

  const handleUserUpdate = (updatedUser) => {
    // Обновляем данные пользователя после верификации
    setUserData(updatedUser);
    
    if (typeof window !== 'undefined') {
      localStorage.setItem('userData', JSON.stringify(updatedUser));
    }
  };

  const handleLogout = async () => {
    // Отправляем запрос на сервер для отзыва refresh токена
    if (refreshToken) {
      try {
        await fetch('http://localhost:8000/logout', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            refresh_token: refreshToken
          })
        });
      } catch (error) {
        console.error('Ошибка при выходе:', error);
      }
    }

    // Очищаем состояние и localStorage
    setIsAuthenticated(false);
    setUserData(null);
    setAccessToken(null);
    setRefreshToken(null);
    
    if (typeof window !== 'undefined') {
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('userData');
    }
  };

  return (
    <div className="">
      {isAuthenticated ? (
        <MainPage 
          userData={userData}
          accessToken={accessToken}
          onLogout={handleLogout}
          onUserUpdate={handleUserUpdate}
        />
      ) : isLogin ? (
        <LoginPage 
          onSwitch={() => setIsLogin(false)}
          onSuccess={handleSuccessfulAuth}
        />
      ) : (
        <RegisterPage 
          onSwitch={() => setIsLogin(true)} 
          onSuccess={handleSuccessfulAuth}
        />
      )}
    </div>
  );
}
