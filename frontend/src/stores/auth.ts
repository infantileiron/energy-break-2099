import type {User} from '../types/domain';import {request} from '../api/client';
export function currentUser():User|null{return JSON.parse(localStorage.getItem('energy-user')||'null')}
export async function login(email:string,password:string){const r=await request('/auth/login','POST',{email,password});localStorage.setItem('energy-token',r.token);localStorage.setItem('energy-user',JSON.stringify(r.user));return r.user}
export function logout(){localStorage.removeItem('energy-token');localStorage.removeItem('energy-user');location.hash='#/login'}
export const canWrite=()=>currentUser()?.role!=='viewer';export const isAdmin=()=>currentUser()?.role==='admin';
