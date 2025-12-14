
// this file is generated — do not edit it


declare module "svelte/elements" {
	export interface HTMLAttributes<T> {
		'data-sveltekit-keepfocus'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-noscroll'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-preload-code'?:
			| true
			| ''
			| 'eager'
			| 'viewport'
			| 'hover'
			| 'tap'
			| 'off'
			| undefined
			| null;
		'data-sveltekit-preload-data'?: true | '' | 'hover' | 'tap' | 'off' | undefined | null;
		'data-sveltekit-reload'?: true | '' | 'off' | undefined | null;
		'data-sveltekit-replacestate'?: true | '' | 'off' | undefined | null;
	}
}

export {};


declare module "$app/types" {
	export interface AppTypes {
		RouteId(): "/";
		RouteParams(): {
			
		};
		LayoutParams(): {
			"/": Record<string, never>
		};
		Pathname(): "/";
		ResolvedPathname(): `${"" | `/${string}`}${ReturnType<AppTypes['Pathname']>}`;
		Asset(): "/favicon.svg" | "/main.js" | "/models/hand_landmarker.task" | "/models/pose_landmarker_lite.task" | "/qr_code/qr-code-004687e2def04456b0e2da5ea11bea30.png" | "/qr_code/qr-code-021d12f79a5c4179be8ef68ae8740533.png" | "/qr_code/qr-code-08a13969402a413abb3dc173ed6bc984.png" | "/qr_code/qr-code-0cd2f38ab36e4ef8b70ce6d37bf52ef9.png" | "/qr_code/qr-code-1c2ae07a3c734f5c8d21fa80b4ce4cb2.png" | "/qr_code/qr-code-225d8220d02d474eaa7191392f57d78e.png" | "/qr_code/qr-code-393c5fc4db2b482d9cbfd134fc005723.png" | "/qr_code/qr-code-574617bf8f8947e39180656f21da2eef.png" | "/qr_code/qr-code-67acfc872eb94bffb38d44526514240f.png" | "/qr_code/qr-code-7003bdfb22f244ba9962d1fa3707efde.png" | "/qr_code/qr-code-758f7df261e5496c8b9915aadaf4e430.png" | "/qr_code/qr-code-7ebd909e113043af941d75b3fdde92f9.png" | "/qr_code/qr-code-93eb4771e4af4ec1b4caa3905622c69c.png" | "/qr_code/qr-code-a9d5c46650cb41daa0fb4d267ed14609.png" | "/qr_code/qr-code-afb358d80b2243f1b9efd6acc949035f.png" | "/qr_code/qr-code-b1a79bd2ff6e475b8ceb109898da56aa.png" | "/qr_code/qr-code-c85e3936afaa49749cbba5b155c69504.png" | "/qr_code/qr-code-d5e3aa1a53cf4489ac4c267f01838f23.png" | "/qr_code/qr-code-ec96c02744634ac2bb724066ff8f9a71.png" | "/style.css" | string & {};
	}
}