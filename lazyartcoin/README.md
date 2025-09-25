# LazyArtCoin (LAC) Launch Kit

LazyArtCoin (LAC) is the native ERC-20 token for the LazyArt platform. This launch kit contains everything you need to deploy the token to Ethereum mainnet and ship a marketing-ready website that onboards contributors and collectors.

## Contents

```
lazyartcoin/
├── README.md                 # This guide
├── token/                    # Hardhat project for the ERC-20 smart contract
└── website/                  # Static marketing site with wallet-enabled dashboard & control center
```

---

## 1. ERC-20 smart contract (`lazyartcoin/token`)

### Key features

- OpenZeppelin-based ERC-20 with burn, permit (EIP-2612), pausable transfers, and multisig-friendly ownership controls.
- Treasury-aware minting helpers to keep operational distribution transparent.
- Hardened constructor arguments (cannot deploy with zero addresses).
- Mainnet-ready Hardhat configuration with scripts for deployment and verification.

### Prerequisites

1. Install Node.js 18+ and npm.
2. Copy `.env.example` to `.env` and fill in production credentials:

   ```
   cd lazyartcoin/token
   cp .env.example .env
   ```

   | Variable | Purpose |
   |----------|---------|
   | `MAINNET_RPC_URL` | HTTPS endpoint for an Ethereum mainnet node (Infura, Alchemy, QuickNode, etc.). |
   | `SEPOLIA_RPC_URL` | Optional testnet endpoint for rehearsals. |
   | `DEPLOYER_PRIVATE_KEY` | Hex-string private key (0x-prefixed) for the deployer wallet. Fund with ETH. |
   | `OWNER_ADDRESS` | (Optional) Address that should own the contract post-deploy. Defaults to deployer. |
   | `TREASURY_ADDRESS` | (Optional) Treasury wallet for minted supply. Defaults to owner. |
   | `INITIAL_SUPPLY` | (Optional) Whole-token amount (no decimals) to mint at deployment. |
   | `ETHERSCAN_API_KEY` | Needed to verify the contract on Etherscan. |

3. Install dependencies:

   ```bash
   npm install
   ```

### Deploying the token

1. **Dry run on Sepolia (recommended)**

   ```bash
   npm run deploy:sepolia
   ```

   After the transaction confirms, copy the address printed in the console and verify if desired:

   ```bash
   npm run verify:sepolia -- <ADDRESS> <OWNER> <TREASURY> <INITIAL_SUPPLY>
   ```

2. **Launch on Ethereum mainnet**

   ```bash
   npm run deploy:mainnet
   ```

   Verification command:

   ```bash
   npm run verify:mainnet -- <ADDRESS> <OWNER> <TREASURY> <INITIAL_SUPPLY>
   ```

   Replace `<INITIAL_SUPPLY>` with the same whole-token number you passed during deployment (for example `1000000`).

### Post-deploy checklist

- Transfer contract ownership to a Safe multisig used by the LazyArt core team:

  ```
  npx hardhat console --network mainnet
  > const token = await ethers.getContractAt("LazyArtCoin", "<TOKEN_ADDRESS>");
  > await token.transferOwnership("<SAFE_ADDRESS>");
  ```

- Seed the treasury with LAC if you skipped initial minting:

  ```
  > await token.mintToTreasury(250000); // Mints 250,000 LAC to the treasury
  ```

- If you need precise control over decimals (for example, 1.5 LAC), use `mintRaw` and pass values in wei (1 LAC = `ethers.parseUnits("1", 18)`).

- Publish the official contract address on lazy.art, your docs, and social media.

- Create a Uniswap pool (LAC/WETH) and seed liquidity for market discovery.

- Submit metadata to Etherscan (logo, description, links) to improve wallet UX.

### File reference

- `contracts/LazyArtCoin.sol` – smart contract source.
- `scripts/deploy.js` – deployment helper that reads env vars and deploys the contract.
- `hardhat.config.js` – compiler, optimizer, and mainnet/sepolia network settings.
- `.env.example` – template for sensitive configuration.

---

## 2. Marketing & dashboard site (`lazyartcoin/website`)

The website is a static bundle that you can host on Vercel, Netlify, GitHub Pages, or any SPA-friendly host. It includes:

- Hero and explainer sections tailored to LazyArtCoin branding.
- Launch checklist that mirrors the Hardhat workflow.
- FAQ for community transparency.
- Wallet-enabled dashboard that connects via MetaMask and reads live LAC balances using `ethers.js`.
- A control center (`settings.html`) that guides you through deployment, treasury minting, and pause controls—no CLI required once your wallet is funded.

### Local preview

```
cd lazyartcoin/website
python3 -m http.server 8081
# Visit http://localhost:8081
```

Open `settings.html` in the same preview to access the control center (for example `http://localhost:8081/settings.html`).

### Customisation tips

- Update `index.html` copy or imagery (`assets/img/lazy-artist.svg`) to match future campaigns.
- Styling lives inside `assets/css/styles.css`. Colors and gradients are defined at the top using CSS variables.
- Behaviour (wallet connection, balance lookups) sits inside `assets/js/main.js`. Swap in your deployed contract address or extend the dashboard with additional analytics.
- Deployment + admin logic lives in `assets/js/settings.js`. It consumes the compiled artifact located at `assets/abi/LazyArtCoin.json`.

### Going live

1. Upload the `website/` directory contents to your hosting provider.
2. Configure HTTPS + a custom domain (for example `https://token.lazy.art`).
3. Optional: add analytics and newsletter embeds for community growth.
4. Share the `settings.html` link privately with the ops team; never post your deployment dashboard publicly.

---

## 3. Operations & governance playbook

- **Treasury management:** Use `mintToTreasury` for campaign allocations. All amounts are in whole tokens; the contract handles decimal scaling internally.
- **AI service billing:** Convert usage metrics (seconds of audio, prompt tokens, storage) to LAC via your backend, then debit users by transferring LAC to the treasury.
- **Emergency pause:** If compromised credentials or suspicious activity occurs, call `pause()` from the multisig. Resume with `unpause()` once resolved.
- **Auditing:** Run `npx hardhat test` after you add tests, and consider `npx hardhat coverage` or `slither .` for static analysis.
- **Compliance:** Consult counsel before mass distributions or token sales. Document tokenomics, vesting, and burn schedules in public-facing materials.
- **Security:** Never paste private keys into the control center. All privileged calls must be signed inside MetaMask (or another hardware wallet connected to MetaMask).

---

## 4. Next steps

1. Deploy to Sepolia and mainnet following the scripts above.
2. Wire LazyArt backend (`app/`) to use LAC transfer flows once the contract address is live.
3. Integrate the website dashboard inside your main domain navigation.
4. Schedule a security review and announce the launch to your community.
