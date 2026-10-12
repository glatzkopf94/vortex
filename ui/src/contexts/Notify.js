import React from 'react';

const NotifyContext = React.createContext({
	Dispatch: () => {},
});

export const NotifyProvider = NotifyContext.Provider;
export const NotifyConsumer = NotifyContext.Consumer;

export default NotifyContext;

// Report status transitions once, using the existing viewport notification.
export function useStatusNotifications(events, ignoreInitial = []) {
 const notify = React.useContext(NotifyContext);
 const previous = React.useRef({});
 const initialized = React.useRef(false);
 React.useEffect(() => {
  const next = {};
  for (const [key, event] of Object.entries(events)) {
   const signature = event ? JSON.stringify(event) : '';
   next[key] = signature;
   if (event && (initialized.current || !ignoreInitial.includes(key)) && signature !== previous.current[key]) {
    notify.Dispatch(event.severity, key, event.message);
   }
  }
  previous.current = next;
  initialized.current = true;
 });
}
