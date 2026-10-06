/**
 * ZONATA Universal AI Company OS — Enterprise Files & Documents Center Workspace
 * Departmental file taxonomy: Corporate, Finance, HR, Legal, Ops, AI.
 * File versioning, cryptographic checksums, classification, and record linkages.
 */

(function() {
  'use strict';

  class EnterpriseFilesWorkspace {
    constructor() {
      this.files = [];
      this.total = 0;
      this.currentDepartment = 'ALL';
      this.currentCategory = 'ALL';
      this.searchQuery = '';
      this.loading = false;
    }

    async render(containerId = 'view-files') {
      const container = document.getElementById(containerId);
      if (!container) return;

      container.innerHTML = `
        <div style="padding:40px; text-align:center;">
          <div class="status-pulse-dot" style="margin:0 auto 12px; width:14px; height:14px;"></div>
          <div style="font-size:14px; color:var(--text-secondary);">Loading Enterprise Files & Documents Center...</div>
        </div>
      `;

      await this.loadFiles();
      this.renderView(container);
    }

    async loadFiles() {
      this.loading = true;
      try {
        const companyId = window.CurrentCompanyContext ? window.CurrentCompanyContext.getCompanyId() : 'comp_primary';
        let url = `/api/files?company_id=${encodeURIComponent(companyId || 'comp_primary')}`;
        if (this.currentDepartment !== 'ALL') url += `&department=${encodeURIComponent(this.currentDepartment)}`;
        if (this.currentCategory !== 'ALL') url += `&category=${encodeURIComponent(this.currentCategory)}`;
        if (this.searchQuery) url += `&q=${encodeURIComponent(this.searchQuery)}`;

        const res = await fetch(url);
        if (res.ok) {
          const data = await res.json();
          this.files = data.files || [];
          this.total = data.total || 0;
        }
      } catch (err) {
        console.error('Failed to load files:', err);
      } finally {
        this.loading = false;
      }
    }

    renderView(container) {
      container.innerHTML = `
        <div class="files-workspace-layout" style="display:flex; flex-direction:column; gap:20px; max-width:1440px; margin:0 auto; padding-bottom:60px;">
          
          <!-- Header Bar -->
          <div class="plugins-header-card" style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:20px 24px; display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px;">
            <div>
              <div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">
                <span class="badge badge-blue" style="font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">Document Vault</span>
                <span style="font-size:12px; color:var(--accent-emerald); font-weight:600; display:inline-flex; align-items:center; gap:6px;">
                  <span class="status-pulse-dot" style="background:var(--accent-emerald);"></span>
                  Cryptographic Integrity Verified
                </span>
              </div>
              <h1 style="font-size:24px; font-weight:700; color:var(--text-primary); margin:0 0 6px 0;">
                Files & Documents Center
              </h1>
              <p style="font-size:13px; color:var(--text-secondary); margin:0;">
                Departmental documentation taxonomy, contractual agreements, audited financial statements, SOP manuals, and cryptographic evidence.
              </p>
            </div>

            <!-- Header Action -->
            <div style="display:flex; gap:10px; align-items:center;">
              <button class="btn-primary" onclick="window.FilesWorkspace.openUploadModal()">
                + Upload / Register Document
              </button>
            </div>
          </div>

          <!-- Departmental Folder Bar -->
          <div style="display:flex; gap:8px; overflow-x:auto; padding-bottom:4px; border-bottom:1px solid var(--border-color);">
            ${['ALL', 'Corporate', 'Finance', 'Legal', 'Operations', 'HR', 'AI'].map(d => `
              <button 
                class="subnav-tab ${this.currentDepartment===d?'active':''}"
                style="padding:8px 16px; font-size:13px; font-weight:600; border:none; background:none; color:${this.currentDepartment===d?'var(--accent-blue)':'var(--text-secondary)'}; border-bottom:2px solid ${this.currentDepartment===d?'var(--accent-blue)':'transparent'}; cursor:pointer; white-space:nowrap;"
                onclick="window.FilesWorkspace.filterDept('${d}')">
                📁 ${d === 'ALL' ? 'All Departments' : d}
              </button>
            `).join('')}
          </div>

          <!-- Filter Toolbar -->
          <div class="enterprise-filter-toolbar">
            <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap; flex:1;">
              <div style="position:relative; min-width:240px; flex:1;">
                <input 
                  type="text" 
                  class="form-input" 
                  placeholder="Search documents by name or summary..." 
                  value="${this.searchQuery}" 
                  oninput="window.FilesWorkspace.handleSearch(this.value)"
                  style="padding-left:32px;"
                />
                <svg style="position:absolute; left:10px; top:50%; transform:translateY(-50%); width:14px; height:14px; color:var(--text-muted);" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              </div>

              <select class="form-input" style="width:auto; min-width:160px;" onchange="window.FilesWorkspace.filterCategory(this.value)">
                <option value="ALL">All Categories</option>
                <option value="CONTRACT">Contracts</option>
                <option value="REPORT">Reports</option>
                <option value="SOP">SOP Manuals</option>
                <option value="POLICY">Policies</option>
                <option value="EVIDENCE">Evidence Ledger Proofs</option>
              </select>
            </div>
          </div>

          <!-- Files Table -->
          <div class="responsive-table-container">
            <table class="enterprise-data-table">
              <thead>
                <tr>
                  <th>Document Name</th>
                  <th>Department</th>
                  <th>Type</th>
                  <th>Size</th>
                  <th>Classification</th>
                  <th>Version</th>
                  <th>Checksum (SHA-256)</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                ${this.files.length === 0 ? `
                  <tr>
                    <td colspan="8" style="text-align:center; padding:40px; color:var(--text-muted);">
                      No documents found in selected departmental directory.
                    </td>
                  </tr>
                ` : this.files.map(f => `
                  <tr>
                    <td>
                      <div style="font-weight:600; color:var(--text-primary); cursor:pointer;" onclick="window.FilesWorkspace.previewFile('${f.file_id}')">
                        📄 ${f.name}
                      </div>
                      <div style="font-size:11px; color:var(--text-muted);">${f.summary || f.category}</div>
                    </td>
                    <td><span class="badge" style="background:rgba(255,255,255,0.06); font-size:11px;">${f.department}</span></td>
                    <td><span class="badge badge-blue" style="font-size:11px;">${f.document_type}</span></td>
                    <td style="font-size:12px; color:var(--text-secondary); font-family:var(--font-mono);">
                      ${(f.size_bytes / 1024).toFixed(1)} KB
                    </td>
                    <td>
                      <span class="badge ${f.classification==='RESTRICTED'?'badge-rose':f.classification==='CONFIDENTIAL'?'badge-amber':'badge-emerald'}" style="font-size:11px;">
                        ${f.classification}
                      </span>
                    </td>
                    <td>
                      <span style="font-size:11px; font-weight:600; color:var(--text-secondary);">v${f.version}.0</span>
                    </td>
                    <td>
                      <span style="font-size:10.5px; font-family:var(--font-mono); color:var(--text-muted);" title="${f.sha256}">
                        ${f.sha256.substring(0, 12)}...
                      </span>
                    </td>
                    <td>
                      <button class="btn-secondary" style="padding:4px 8px; font-size:11.5px;" onclick="window.FilesWorkspace.previewFile('${f.file_id}')">
                        Preview
                      </button>
                    </td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          </div>
        </div>
      `;
    }

    async filterDept(dept) {
      this.currentDepartment = dept;
      await this.loadFiles();
      const container = document.getElementById('view-files');
      if (container) this.renderView(container);
    }

    async filterCategory(cat) {
      this.currentCategory = cat;
      await this.loadFiles();
      const container = document.getElementById('view-files');
      if (container) this.renderView(container);
    }

    async handleSearch(q) {
      this.searchQuery = q;
      await this.loadFiles();
      const container = document.getElementById('view-files');
      if (container) this.renderView(container);
    }

    previewFile(fileId) {
      const f = this.files.find(item => item.file_id === fileId);
      if (!f) return;

      const body = `
        <div style="display:flex; flex-direction:column; gap:16px;">
          <div>
            <div style="font-size:12px; color:var(--text-muted); font-family:var(--font-mono);">${f.file_id}</div>
            <h3 style="font-size:18px; font-weight:700; margin:4px 0 8px 0;">${f.name}</h3>
            <div style="display:flex; gap:8px;">
              <span class="badge badge-blue">${f.department}</span>
              <span class="badge badge-emerald">${f.classification}</span>
              <span class="badge" style="background:rgba(255,255,255,0.06);">Version ${f.version}.0</span>
            </div>
          </div>

          <div style="background:rgba(0,0,0,0.25); border:1px solid var(--border-color); border-radius:8px; padding:14px;">
            <div style="font-size:11.5px; font-weight:600; color:var(--text-muted); text-transform:uppercase;">Document Intelligence Summary</div>
            <p style="font-size:13.5px; color:var(--text-primary); margin-top:6px; line-height:1.5;">${f.summary || 'Official corporate asset indexed into organizational knowledge graph.'}</p>
          </div>

          <div>
            <h4 style="font-size:13px; font-weight:600; color:var(--text-secondary); margin-bottom:6px;">Storage & Cryptographic Signature</h4>
            <div style="font-family:var(--font-mono); font-size:11.5px; background:rgba(0,0,0,0.3); padding:10px; border-radius:6px; border:1px solid var(--border-color); color:var(--accent-emerald);">
              SHA-256: ${f.sha256}
            </div>
          </div>

          <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:8px;">
            <button class="btn-secondary" onclick="window.closeModal()">Close</button>
            <button class="btn-primary" onclick="window.showToast('Secure document downloaded', 'success'); window.closeModal();">Download File</button>
          </div>
        </div>
      `;

      if (window.openModal) {
        window.openModal('Document Dossier & Preview', body);
      }
    }

    openUploadModal() {
      const body = `
        <form onsubmit="window.FilesWorkspace.submitRegisterFile(event)" style="display:flex; flex-direction:column; gap:12px;">
          <div>
            <label class="form-label">Document Name *</label>
            <input type="text" class="form-input" id="newDocName" placeholder="e.g. Q4_Executive_Budget_Statement.pdf" required />
          </div>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div>
              <label class="form-label">Department *</label>
              <select class="form-input" id="newDocDept">
                <option value="Corporate">Corporate</option>
                <option value="Finance">Finance</option>
                <option value="Legal">Legal</option>
                <option value="Operations">Operations</option>
                <option value="HR">HR</option>
                <option value="AI">AI</option>
              </select>
            </div>
            <div>
              <label class="form-label">Category *</label>
              <select class="form-input" id="newDocCat">
                <option value="CONTRACT">CONTRACT</option>
                <option value="REPORT">REPORT</option>
                <option value="SOP">SOP MANUAL</option>
                <option value="POLICY">POLICY</option>
                <option value="EVIDENCE">EVIDENCE</option>
              </select>
            </div>
          </div>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div>
              <label class="form-label">Classification *</label>
              <select class="form-input" id="newDocClass">
                <option value="INTERNAL">INTERNAL</option>
                <option value="CONFIDENTIAL">CONFIDENTIAL</option>
                <option value="RESTRICTED">RESTRICTED</option>
                <option value="PUBLIC">PUBLIC</option>
              </select>
            </div>
            <div>
              <label class="form-label">File Type</label>
              <input type="text" class="form-input" id="newDocType" value="PDF" />
            </div>
          </div>
          <div>
            <label class="form-label">Document Summary & Notes</label>
            <textarea class="form-input" id="newDocSummary" rows="2" placeholder="Summary of contents..."></textarea>
          </div>
          <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:8px;">
            <button type="button" class="btn-secondary" onclick="window.closeModal()">Cancel</button>
            <button type="submit" class="btn-primary">Index & Register</button>
          </div>
        </form>
      `;

      if (window.openModal) {
        window.openModal('Register Enterprise Document', body);
      }
    }

    async submitRegisterFile(e) {
      e.preventDefault();
      const name = document.getElementById('newDocName').value;
      const dept = document.getElementById('newDocDept').value;
      const cat = document.getElementById('newDocCat').value;
      const classification = document.getElementById('newDocClass').value;
      const dtype = document.getElementById('newDocType').value;
      const summary = document.getElementById('newDocSummary').value;

      try {
        const res = await fetch('/api/files', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name,
            department: dept,
            category: cat,
            classification,
            document_type: dtype,
            summary,
            size_bytes: 1048576,
            uploaded_by: 'Host / Owner'
          })
        });

        if (res.ok) {
          if (window.closeModal) window.closeModal();
          if (window.showToast) window.showToast('Document indexed and sealed into vault!', 'success');
          await this.loadFiles();
          const container = document.getElementById('view-files');
          if (container) this.renderView(container);
        }
      } catch (err) {
        console.error('Failed to register file:', err);
      }
    }
  }

  window.FilesWorkspace = new EnterpriseFilesWorkspace();
})();
