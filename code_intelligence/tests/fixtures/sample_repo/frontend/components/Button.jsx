import React from "react";

export function Button({ label, onClick }) {
  return <button onClick={onClick}>{label}</button>;
}

export const IconButton = ({ icon }) => {
  return <button>{icon}</button>;
};
