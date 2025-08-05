const ngrok = require('ngrok');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

async function updateShopifyConfig(publicUrl) {
    // Find shopify.app.*.toml file
    const configFiles = fs.readdirSync(__dirname).filter(file => 
        file.startsWith('shopify.app.') && file.endsWith('.toml')
    );
    
    if (configFiles.length === 0) {
        console.error('❌ No shopify.app.*.toml file found');
        return;
    }
    
    const configPath = path.join(__dirname, configFiles[0]);
    let config = fs.readFileSync(configPath, 'utf8');
    
    config = config.replace(/application_url = ".*"/, `application_url = "${publicUrl}/auth"`);
    config = config.replace(/redirect_urls = \[ ".*" \]/, `redirect_urls = [ "${publicUrl}/auth/callback" ]`);
    // Add include_config_on_deploy = true if not present
    if (!config.includes('include_config_on_deploy = true')) {
        // Find the end of the file and add the build section
        if (!config.includes('[build]')) {
            config += '\n[build]\ninclude_config_on_deploy = true\n';
        } else {
            // If [build] section exists, add the option to it
            config = config.replace(/\[build\]/, '[build]\ninclude_config_on_deploy = true');
        }
    }
    // Handle webhook subscription
    if (config.includes('["app/uninstalled"]')) {
        // Update existing webhook URI - be more specific to match only the app/uninstalled webhook
        const webhookRegex = /(\[\[webhooks\.subscriptions\]\]\s*topics\s*=\s*\["app\/uninstalled"\]\s*uri\s*=\s*)"[^"]*"/;
        if (webhookRegex.test(config)) {
            config = config.replace(webhookRegex, `$1"${publicUrl}/webhooks/uninstalled"`);
        }
    } else {
        // Add new webhook subscription
        config += `\n[[webhooks.subscriptions]]\ntopics = ["app/uninstalled"]\nuri = "${publicUrl}/webhooks/uninstalled"`;
    }
    
    fs.writeFileSync(configPath, config);
    console.log(`✅ Updated ${configFiles[0]}: ${publicUrl}`);
}

async function updateEnvFile(publicUrl) {
    const envPath = path.join(__dirname, 'backend', '.env');
    
    if (!fs.existsSync(envPath)) {
        const envTemplate = `APP_CLIENT_ID=your_shopify_app_client_id
APP_CLIENT_SECRET=your_shopify_app_client_secret
APP_REDIRECT_URI=${publicUrl}/auth/callback
APP_SCOPES=read_products,write_products
SECRET_KEY=your_secret_key_here
`;
        fs.writeFileSync(envPath, envTemplate);
        return;
    }
    
    let envContent = fs.readFileSync(envPath, 'utf8');
    
    if (envContent.includes('APP_REDIRECT_URI=')) {
        envContent = envContent.replace(/APP_REDIRECT_URI=.*$/m, `APP_REDIRECT_URI=${publicUrl}/auth/callback`);
    } else {
        envContent += `\nAPP_REDIRECT_URI=${publicUrl}/auth/callback`;
    }
    
    fs.writeFileSync(envPath, envContent);
    console.log(`✅ Updated .env: ${publicUrl}/auth/callback`);
    console.log(`📝 .env file path: ${envPath}`);
}

async function startNgrok() {
    try {
        console.log('🚀 Starting ngrok...');
        const publicUrl = await ngrok.connect({
            addr: 5000
        });

        console.log(`🌐 ${publicUrl}`);
        await updateShopifyConfig(publicUrl);
        await updateEnvFile(publicUrl);

        const deployProcess = spawn('npx', ['shopify', 'app', 'deploy', '-f'], {
            stdio: 'inherit',
            shell: true
        });

        deployProcess.on('close', (code) => {
            if (code === 0) {
                console.log('✅ Deploy complete, starting services...');
                
                const child = spawn('npx', ['concurrently', '"npm run dev:backend"', '"npm run dev:frontend"'], {
                    stdio: 'inherit',
                    shell: true
                });

                process.on('SIGINT', async () => {
                    child.kill('SIGINT');
                    await ngrok.kill();
                    process.exit(0);
                });
            } else {
                console.error('❌ Deploy failed');
                process.exit(code);
            }
        });

        process.on('SIGINT', async () => {
            deployProcess.kill('SIGINT');
            await ngrok.kill();
            process.exit(0);
        });

    } catch (error) {
        console.error('❌ Error:', error.message);
        process.exit(1);
    }
}

startNgrok();
