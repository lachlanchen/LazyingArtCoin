# LazyArtCoin Test Kit (Sepolia)

This folder mirrors the production LazyArtCoin launcher but targets the Sepolia Ethereum testnet. Use it to rehearse deployments, distribute test credits to users, and validate the full MetaMask-driven control center before touching mainnet.

## Structure

```
lazyartcoin_test/
├── README.md
├── token/             # Hardhat project configured for Sepolia
└── website/           # Static site & control center pointed at the testnet
```

---

## 1. Test ERC-20 (`lazyartcoin_test/token`)

### What it does

- Deploys the same `LazyArtCoin` contract to Sepolia.
- Defaults to Sepolia RPC and scripts, so you never risk mainnet funds while testing.
- Lets you mint test allocations to friends and creators so they experience the credit flow.

### Before you start

1. **Fund a MetaMask test account with Sepolia ETH.**
   - Visit an official faucet (e.g., [https://sepolia-faucet.pk910.de/](https://sepolia-faucet.pk910.de/)) and send ETH to your MetaMask account.
2. **Copy the env template:**

   ```bash
   cd lazyartcoin_test/token
   cp .env.example .env
   ```

3. **Populate `.env`:**

   | Key | What to enter |
   |-----|----------------|
   | `SEPOLIA_RPC_URL` | HTTPS endpoint for Sepolia (Infura/Alchemy/etc.). |
   | `DEPLOYER_PRIVATE_KEY` | `0x`-prefixed private key for the MetaMask account holding test ETH. |
   | `OWNER_ADDRESS` | (Optional) Multisig or teammate account that should control the token. Default: deployer. |
   | `TREASURY_ADDRESS` | (Optional) Wallet receiving the initial supply. Default: owner. |
   | `INITIAL_SUPPLY` | Whole LAC amount to mint at deploy (e.g., `1000000`). |
   | `ETHERSCAN_API_KEY` | Optional key for Sepolia verification. |

4. **Install dependencies:**

   ```bash
   npm install
   ```

### Deploy to Sepolia

```bash
npm run deploy:sepolia
```

- Confirm the transaction in MetaMask when prompted.
- After deployment finishes, note the contract address printed in the console.

### Verify on Sepolia Etherscan (optional)

```bash
npm run verify:sepolia -- <DEPLOYED_ADDRESS> <OWNER> <TREASURY> <INITIAL_SUPPLY>
```

> If verification fails, double-check that the constructor parameters match exactly what you used.

### Common follow-ups

- **Mint more test LAC:**

  ```bash
  npx hardhat console --network sepolia
  > const token = await ethers.getContractAt("LazyArtCoin", "<TOKEN_ADDRESS>");
  > await token.mintTo("<RECIPIENT>", 5000n);
  ```

- **Pause/unpause:** use `token.pause()` or `token.unpause()`—handy for rehearsing incident playbooks.

- **Transfer ownership to a Safe** if you want to test multisig flows.

---

## 2. Test website (`lazyartcoin_test/website`)

The site is a carbon copy of the production marketing page plus the control center, but every checklist and dropdown defaults to Sepolia.

### Local preview

```bash
cd lazyartcoin_test/website
python3 -m http.server 8090
# Visit http://localhost:8090
# Control center: http://localhost:8090/settings.html
```

> MetaMask works on `http://localhost`, so HTTPS is not required for local testing. Use ngrok or a hosting provider with TLS if you want to share the test dashboard externally.

### Deploy checklist (Sepolia)

1. Load `settings.html`, connect MetaMask, and ensure the network shows **Sepolia Testnet**.
2. Fill the owner, treasury, and initial supply fields if you want to override defaults. Keep them blank to reuse your connected wallet.
3. Hit **Deploy LazyArtCoin** and approve the transaction (test ETH only).
4. Once confirmed, the contract address auto-saves and can be used to mint allocations, pause, unpause, etc.
5. Share the control center with teammates so they can mint test LAC to their own wallets and simulate payouts.

### Files to know

- `website/index.html` – Hero/testnet messaging.
- `website/settings.html` – Control center UI for Sepolia.
- `website/assets/js/settings.js` – Wallet logic tuned for Sepolia by default.
- `website/assets/abi/LazyArtCoin.json` – ABI pulled from the test Hardhat build.

---

## 3. Prepare these items before inviting testers

1. **Test wallet funded with Sepolia ETH (MetaMask).**
2. **RPC endpoint** (Infura/Alchemy project) added to `.env`.
3. **Optional multisig or secondary wallet** if you want to rehearse ownership transfers.
4. **List of tester addresses** to mint LAC to once deployed.
5. **Communication plan** telling testers how to add the token to MetaMask:
   - MetaMask → Import tokens → Paste the Sepolia contract address.
6. **Explorer link** (https://sepolia.etherscan.io/address/`<token_address>`) ready to share for transparency.

With these in place, testers can hold and transfer LazyArtCoin on Sepolia exactly like a mainnet asset, giving them the full experience without risking real funds.
