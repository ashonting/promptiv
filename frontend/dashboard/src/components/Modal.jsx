// frontend/dashboard/src/components/Modal.jsx
import React from "react";

const Modal = ({ open, onClose, children }) => {
  if (!open) return null;
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 2000,
        background: "rgba(40,48,80,0.29)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center"
      }}
      onClick={onClose}
      aria-modal="true"
      role="dialog"
    >
      <div
        style={{
          background: "#fff",
          borderRadius: 14,
          boxShadow: "0 12px 44px #344b9552",
          padding: "2.5rem 2rem 2rem 2rem",
          minWidth: 330,
          maxWidth: 430,
          width: "90%",
          position: "relative"
        }}
        onClick={e => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          style={{
            position: "absolute",
            top: 13,
            right: 17,
            background: "none",
            border: "none",
            fontSize: 22,
            fontWeight: 700,
            color: "#7c87b3",
            cursor: "pointer",
            lineHeight: 1,
          }}
          aria-label="Close"
        >&times;</button>
        {children}
      </div>
    </div>
  );
};

export default Modal;
