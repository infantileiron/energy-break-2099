import {useEffect} from "react";export function usePolling(load:()=>Promise<unknown>,ms=2000){useEffect(()=>{const timer=setInterval(()=>void load(),ms);return()=>clearInterval(timer)},[load,ms])}
