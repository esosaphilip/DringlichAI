export default function Toast({ message, canUndo, undoLabel, onUndo }) {
  return (
    <div className="toast" role="status">
      <span className="toast-msg">{message}</span>
      {canUndo && (
        <button type="button" className="toast-undo" onClick={onUndo}>
          {undoLabel}
        </button>
      )}
    </div>
  )
}
