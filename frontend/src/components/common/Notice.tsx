export default function Notice({message}:{message:string}){return message?<div className="notice" role="alert">{message}<small>请调整输入后重试。</small></div>:null}
