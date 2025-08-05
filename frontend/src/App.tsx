import { useState } from 'react'
import './App.css'


const App = () => {
  const [message, setMessage] = useState("")
  const fetchCall = () => {
    fetch("/api/hello")
      .then(res => res.json())
      .then(data => {
        setMessage(data.message)
      })
      .catch(err => {
        console.error(err)
      })}
  return (
    <div>
      <div>{message}</div>
      <button onClick={() => setMessage("Hello, this is from frontend!")}>Click me</button>
      <button onClick={fetchCall}>Click me</button>
    </div>
  )
}

export default App